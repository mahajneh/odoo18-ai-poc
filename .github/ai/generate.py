import json
import os
from pathlib import Path

import requests


# -----------------------------
# Helpers
# -----------------------------
def die(msg: str) -> None:
    raise RuntimeError(msg)


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


# -----------------------------
# Main
# -----------------------------
print("=== AI GENERATOR v3 (STRICT JSON SCHEMA) ===")

key = os.environ.get("OPENAI_API_KEY", "")
if not key:
    die("OPENAI_API_KEY missing in GitHub Secrets.")

issue_title = os.environ.get("ISSUE_TITLE", "").strip()
issue_body = os.environ.get("ISSUE_BODY", "").strip()
issue_number = os.environ.get("ISSUE_NUMBER", "0").strip()

if not issue_title:
    issue_title = f"Issue {issue_number}"

# Ensure folders exist (optional)
Path("AI_SPECS").mkdir(parents=True, exist_ok=True)
Path("addons").mkdir(parents=True, exist_ok=True)

module_name = f"ai_issue_{issue_number}"
module_root = f"addons/{module_name}"

# JSON schema: we force the model to return:
# {
#   "files": { "path": "file-content", ... }
# }
schema = {
    "type": "object",
    "properties": {
        "files": {
            "type": "object",
            "additionalProperties": {"type": "string"},
        }
    },
    "required": ["files"],
    "additionalProperties": False,
}

prompt = f"""
You are generating an Odoo addon inside an existing repo.

Return ONLY a JSON object that matches the schema enforced by the API.
The JSON must include "files" mapping of file paths to exact file contents.

Rules:
- All file paths MUST start with "{module_root}/"
- Create at minimum:
  1) "{module_root}/__manifest__.py"
  2) "{module_root}/__init__.py"
  3) "{module_root}/models/__init__.py"
  4) "{module_root}/models/models.py"
- "__manifest__.py" content must be valid Python code containing a dict literal.
- Use Odoo style and imports.
- Implement a model that stores loyalty points per customer:
  - partner_id (Many2one to res.partner, required)
  - points (Integer, default 0)
- No markdown. No explanations.

Issue title: {issue_title}
Issue body:
{issue_body}
""".strip()

# Call OpenAI Responses API with strict JSON schema formatting
r = requests.post(
    "https://api.openai.com/v1/responses",
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    },
    json={
        "model": "gpt-4o-mini",
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "repo_patch",
                "schema": schema,
                "strict": True,
            }
        },
    },
    timeout=180,
)

print("OpenAI status:", r.status_code)

# Always print some response for debugging
raw = r.text or ""
print("OpenAI raw response (first 2000 chars):", raw[:2000])

if r.status_code >= 400:
    die(f"OpenAI API error {r.status_code}: {raw[:2000]}")

data = r.json()
text = extract_output_text(data)

print("Extracted output_text (first 2000 chars):", (text or "")[:2000])

if not text.strip():
    die("OpenAI returned empty output_text. Check raw response above.")

# Parse the strict JSON (guaranteed by schema)
payload = json.loads(text)

files = payload.get("files", {})
if not isinstance(files, dict) or not files:
    die(f"No files returned in payload. Payload keys: {list(payload.keys())}")

# Safety: only allow writing inside the module root
for path_str, content in files.items():
    if not isinstance(path_str, str) or not isinstance(content, str):
        die("Invalid files mapping (paths and contents must be strings).")

    if not path_str.startswith(f"{module_root}/"):
        die(f"Refusing to write outside module root. Got path: {path_str}")

    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

# Write a spec file for traceability
Path(f"AI_SPECS/issue-{issue_number}.md").write_text(
    f"# Issue #{issue_number}\n\n## {issue_title}\n\n{issue_body}\n",
    encoding="utf-8",
)

print(f"✅ Generated {len(files)} files under {module_root}/")
print("✅ Done.")
