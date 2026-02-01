import base64
import json
import os
import re
import subprocess
from pathlib import Path

import requests


# -----------------------------
# Helpers
# -----------------------------
def die(msg: str) -> None:
    raise RuntimeError(msg)


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def extract_output_text(resp_json: dict) -> str:
    """
    Extracts concatenated `output_text` segments from the Responses API payload.
    """
    text = ""
    for item in resp_json.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    text += c.get("text", "")
    return text


def extract_first_json_object(s: str) -> str:
    """
    Fallback extractor: grabs the first JSON object from a blob of text.
    Helps if the model accidentally prints extra text.
    """
    s = s.strip()
    if s.startswith("{") and s.endswith("}"):
        return s

    # naive brace matching
    start = s.find("{")
    if start == -1:
        die("No JSON object found in output.")
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]

    die("Unbalanced JSON braces in output.")


def ensure_git_identity() -> None:
    # Safe defaults for GitHub Actions
    run(["git", "config", "user.name", "github-actions[bot]"], check=False)
    run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], check=False)


def git_has_changes() -> bool:
    r = run(["git", "status", "--porcelain"], check=True)
    return bool(r.stdout.strip())


# -----------------------------
# Main
# -----------------------------
print("=== AI GENERATOR v4 (BASE64 FILES + AUTO COMMIT) ===")

key = os.environ.get("OPENAI_API_KEY", "").strip()
if not key:
    die("OPENAI_API_KEY missing in GitHub Secrets.")

issue_title = os.environ.get("ISSUE_TITLE", "").strip()
issue_body = os.environ.get("ISSUE_BODY", "").strip()
issue_number = os.environ.get("ISSUE_NUMBER", "0").strip()

if not issue_title:
    issue_title = f"Issue {issue_number}"

# IMPORTANT: Your repo layout is Odoo inside /odoo and addons live under /odoo/addons
addons_root = Path("odoo/addons")
addons_root.mkdir(parents=True, exist_ok=True)

Path("AI_SPECS").mkdir(parents=True, exist_ok=True)

module_name = f"ai_issue_{issue_number}"
module_root = addons_root / module_name

# Prompt: force JSON + base64 content to avoid JSONDecodeError
prompt = f"""
You are generating an Odoo 18 addon inside an existing git repo.

Return ONLY valid JSON (no markdown, no explanations) in this exact shape:

{{
  "files_b64": {{
    "odoo/addons/{module_name}/__manifest__.py": "<BASE64_OF_FILE_CONTENT>",
    "odoo/addons/{module_name}/__init__.py": "<BASE64>",
    "odoo/addons/{module_name}/models/__init__.py": "<BASE64>",
    "odoo/addons/{module_name}/models/models.py": "<BASE64>"
  }}
}}

Rules:
- Every path MUST start with "odoo/addons/{module_name}/"
- Provide at least the 4 required files listed above.
- File contents must be UTF-8 text, then BASE64 encoded (standard base64, no newlines).
- "__manifest__.py" must be valid Python dict literal code.
- Odoo 18 manifest rules:
  - version must be "18.0.1.0.1"
  - author must be "mahajneh"
  - website must be "https://mahajneh.com"
- Implement a model that stores loyalty points per customer:
  - partner_id = Many2one('res.partner', required=True)
  - points = Integer(default=0)

Issue title: {issue_title}
Issue body:
{issue_body}
""".strip()

# Call OpenAI Responses API
r = requests.post(
    "https://api.openai.com/v1/responses",
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    },
    json={
        "model": "gpt-4o-mini",
        "input": prompt,
        "temperature": 0,
        "max_output_tokens": 2000,
        "text": {"format": {"type": "text"}},
    },
    timeout=180,
)

print("OpenAI status:", r.status_code)
raw = r.text or ""
print("OpenAI raw response (first 2000 chars):", raw[:2000])

if r.status_code >= 400:
    die(f"OpenAI API error {r.status_code}: {raw[:2000]}")

data = r.json()
out_text = extract_output_text(data)
print("Extracted output_text (first 1200 chars):", (out_text or "")[:1200])

if not out_text.strip():
    die("OpenAI returned empty output_text. Check raw response above.")

# Parse JSON (robust)
json_blob = extract_first_json_object(out_text)
try:
    payload = json.loads(json_blob)
except json.JSONDecodeError as e:
    die(f"JSON parse failed: {e}\nFirst 1200 chars:\n{json_blob[:1200]}")

files_b64 = payload.get("files_b64")
if not isinstance(files_b64, dict) or not files_b64:
    die(f"No files_b64 returned. Payload keys: {list(payload.keys())}")

# Write files safely
written = 0
for path_str, b64 in files_b64.items():
    if not isinstance(path_str, str) or not isinstance(b64, str):
        die("Invalid files_b64 mapping (paths and contents must be strings).")

    if not path_str.startswith(f"odoo/addons/{module_name}/"):
        die(f"Refusing to write outside module root. Got path: {path_str}")

    try:
        content = base64.b64decode(b64.encode("utf-8"), validate=True).decode("utf-8")
    except Exception as e:
        die(f"Failed to base64-decode content for {path_str}: {e}")

    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    written += 1

# Write spec file for traceability
spec_path = Path(f"AI_SPECS/issue-{issue_number}.md")
spec_path.write_text(
    f"# Issue #{issue_number}\n\n## {issue_title}\n\n{issue_body}\n",
    encoding="utf-8",
)

print(f"✅ Generated {written} files under odoo/addons/{module_name}/")
print(f"✅ Wrote {spec_path}")

# -----------------------------
# Git add + commit (CRITICAL)
# -----------------------------
ensure_git_identity()

# Stage only what we touched
run(["git", "add", str(module_root), str(spec_path)])

if not git_has_changes():
    # This prevents "no PR" silent behavior
    die("No git changes detected after generation. Nothing to commit.")

commit_msg = f"AI: implement issue #{issue_number}"
run(["git", "commit", "-m", commit_msg])

print("✅ Committed changes:", commit_msg)
print("✅ Done.")
