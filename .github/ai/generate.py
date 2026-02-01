import json
import os
from pathlib import Path

import requests


def die(msg: str) -> None:
    raise RuntimeError(msg)


def extract_output_text(resp_json: dict) -> str:
    parts = []
    for item in resp_json.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    parts.append(c.get("text", ""))
    return "".join(parts)


print("=== AI GENERATOR v5 (STRICT JSON, NO B64) ===")

key = os.environ.get("OPENAI_API_KEY", "").strip()
if not key:
    die("OPENAI_API_KEY missing in GitHub Secrets.")

issue_title = os.environ.get("ISSUE_TITLE", "").strip()
issue_body = os.environ.get("ISSUE_BODY", "").strip()
issue_number = os.environ.get("ISSUE_NUMBER", "0").strip()

if not issue_title:
    issue_title = f"Issue {issue_number}"

module_name = f"ai_issue_{issue_number}"
module_root = f"odoo/addons/{module_name}"

Path("AI_SPECS").mkdir(parents=True, exist_ok=True)

# STRICT JSON schema: files[path] = string
schema = {
    "type": "object",
    "properties": {
        "files": {
            "type": "object",
            "properties": {},
            "additionalProperties": {"type": "string"},
            "required": [],
        }
    },
    "required": ["files"],
    "additionalProperties": False,
}

prompt = f"""
You are generating an Odoo 18 addon inside an existing repository.

Return ONLY valid JSON matching this structure:
{{
  "files": {{
    "path": "file content as UTF-8 text",
    ...
  }}
}}

Rules:
- ALL file paths MUST start with "{module_root}/"
- Return ONLY these exact files (no more, no less):
  1) "{module_root}/__manifest__.py"
  2) "{module_root}/__init__.py"
  3) "{module_root}/models/__init__.py"
  4) "{module_root}/models/models.py"

Code rules:
- __manifest__.py MUST be a Python dict literal (not JSON) and MUST NOT include print().
- Use:
  author="mahajneh"
  website="https://mahajneh.com"
  version="18.0.1.0.1"
- Odoo model:
  _name = "customer.loyalty"
  partner_id = fields.Many2one("res.partner", required=True)
  points = fields.Integer(default=0)

Output rules:
- No markdown. No explanations. JSON only.
- Ensure all newlines are escaped correctly (\\n) inside JSON strings.

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

if data.get("status") != "completed":
    die(f"OpenAI response not completed. status={data.get('status')}, details={data.get('incomplete_details')}")

out_text = extract_output_text(data)
print("Extracted output_text (first 2000 chars):", (out_text or "")[:2000])

if not out_text.strip():
    die("OpenAI returned empty output_text.")

try:
    payload = json.loads(out_text)
except json.JSONDecodeError as e:
    tail = out_text[-500:] if out_text else ""
    die(f"JSON parse failed: {e}\n--- output tail ---\n{tail}")

files = payload.get("files", {})
if not isinstance(files, dict) or not files:
    die(f"No files returned. Payload keys: {list(payload.keys())}")

written = 0
for path_str, content in files.items():
    if not isinstance(path_str, str) or not isinstance(content, str):
        die("Invalid files mapping (paths and contents must be strings).")

    if not path_str.startswith(f"{module_root}/"):
        die(f"Refusing to write outside module root. Got path: {path_str}")

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
