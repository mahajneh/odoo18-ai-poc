import base64
import json
import os
from pathlib import Path

import requests


def die(msg: str) -> None:
    raise RuntimeError(msg)


def extract_output_text(resp_json: dict) -> str:
    """
    Extract concatenated output_text segments from the Responses API payload.
    """
    parts = []
    for item in resp_json.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    parts.append(c.get("text", ""))
    return "".join(parts)


print("=== AI GENERATOR v4.1 (STRICT JSON + B64 + HIGH TOKENS) ===")

key = os.environ.get("OPENAI_API_KEY", "").strip()
if not key:
    die("OPENAI_API_KEY missing in GitHub Secrets.")

issue_title = os.environ.get("ISSUE_TITLE", "").strip() or "AI Issue"
issue_body = os.environ.get("ISSUE_BODY", "").strip()
issue_number = os.environ.get("ISSUE_NUMBER", "0").strip()

# Repo layout: you are writing under odoo/addons/...
module_name = f"ai_issue_{issue_number}"
module_root = f"odoo/addons/{module_name}"

Path("AI_SPECS").mkdir(parents=True, exist_ok=True)

# Strict JSON schema. IMPORTANT: In strict mode, OpenAI requires:
# - required must be present where used
# - properties must be present where used
schema = {
    "type": "object",
    "properties": {
        "files_b64": {
            "type": "object",
            "properties": {},
            "additionalProperties": {"type": "string"},
            "required": [],
        }
    },
    "required": ["files_b64"],
    "additionalProperties": False,
}

prompt = f"""
You are generating an Odoo 18 addon inside an existing repository.

Return ONLY valid JSON that matches the enforced schema:
{{
  "files_b64": {{
    "path": "base64(file_content_utf8)",
    ...
  }}
}}

Rules:
- ALL file paths MUST start with "{module_root}/"
- Return ONLY these exact paths (no extra files):
  1) "{module_root}/__manifest__.py"
  2) "{module_root}/__init__.py"
  3) "{module_root}/models/__init__.py"
  4) "{module_root}/models/models.py"
- Keep code minimal and correct for Odoo 18.
- __manifest__.py must be a Python dict literal (not JSON).
- Must implement a model:
  - partner_id = fields.Many2one('res.partner', required=True)
  - points = fields.Integer(default=0)
- No markdown. No explanations. JSON only.

Issue title: {issue_title}
Issue body:
{issue_body}
""".strip()

r = requests.post(
    "https://api.openai.com/v1/responses",
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    },
    json={
        "model": "gpt-4o-mini-2024-07-18",
        "input": prompt,
        # IMPORTANT: raise max_output_tokens so response isn't truncated
        "max_output_tokens": 8000,
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
raw = r.text or ""
print("OpenAI raw response (first 2000 chars):", raw[:2000])

if r.status_code >= 400:
    die(f"OpenAI API error {r.status_code}: {raw[:2000]}")

data = r.json()
out_text = extract_output_text(data)
print("Extracted output_text (first 2000 chars):", (out_text or "")[:2000])

# Handle incomplete responses explicitly
if data.get("status") != "completed":
    incomplete = data.get("incomplete_details") or {}
    die(f"OpenAI response not completed. status={data.get('status')}, details={incomplete}")

if not out_text.strip():
    die("OpenAI returned empty output_text.")

try:
    payload = json.loads(out_text)
except json.JSONDecodeError as e:
    tail = out_text[-500:] if out_text else ""
    die(f"JSON parse failed: {e}\n--- output tail ---\n{tail}")

files_b64 = payload.get("files_b64", {})
if not isinstance(files_b64, dict) or not files_b64:
    die(f"No files_b64 returned. Payload keys: {list(payload.keys())}")

# Write module files
written = 0
for path_str, b64 in files_b64.items():
    if not isinstance(path_str, str) or not isinstance(b64, str):
        die("Invalid files_b64 mapping (paths and contents must be strings).")

    if not path_str.startswith(f"{module_root}/"):
        die(f"Refusing to write outside module root. Got path: {path_str}")

    try:
        content = base64.b64decode(b64).decode("utf-8")
    except Exception as e:
        die(f"Base64 decode failed for {path_str}: {e}")

    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    written += 1

Path(f"AI_SPECS/issue-{issue_number}.md").write_text(
    f"# Issue #{issue_number}\n\n## {issue_title}\n\n{issue_body}\n",
    encoding="utf-8",
)

print(f"✅ Generated {written} files under {module_root}/")
print("✅ Done.")
