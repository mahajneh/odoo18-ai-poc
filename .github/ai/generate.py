import os
import json
import requests
from pathlib import Path

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ISSUE_TITLE = os.environ.get("ISSUE_TITLE", "")
ISSUE_BODY = os.environ.get("ISSUE_BODY", "")
ISSUE_NUMBER = os.environ.get("ISSUE_NUMBER", "0")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing. Add it in repo Settings -> Secrets -> Actions.")

# Ensure folders exist
Path("addons").mkdir(exist_ok=True)
Path("AI_SPECS").mkdir(exist_ok=True)

# Force JSON output via schema
schema = {
    "name": "odoo_addon_files",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "files": {
                "type": "object",
                "additionalProperties": {"type": "string"},
            }
        },
        "required": ["files"],
    },
    "strict": True,
}

system_prompt = f"""
You are a senior Odoo 18 developer.

Generate a minimal addon skeleton for the issue.

Rules:
- Output JSON only using the required schema.
- Write ONLY under:
  - addons/ai_issue_{ISSUE_NUMBER}/...
  - AI_SPECS/issue-{ISSUE_NUMBER}.md
- Create at least:
  - addons/ai_issue_{ISSUE_NUMBER}/__manifest__.py
  - addons/ai_issue_{ISSUE_NUMBER}/models/__init__.py
  - addons/ai_issue_{ISSUE_NUMBER}/models/models.py
"""

user_prompt = f"TITLE: {ISSUE_TITLE}\n\nBODY:\n{ISSUE_BODY}"

resp = requests.post(
    "https://api.openai.com/v1/responses",
    headers={
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": "gpt-4o-mini",
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "text": {"format": {"type": "json_schema", "json_schema": schema}},
    },
    timeout=120,
)

# If OpenAI returns an error, show it in logs clearly
if resp.status_code >= 400:
    raise RuntimeError(f"OpenAI API error {resp.status_code}: {resp.text}")

data = resp.json()

# Extract output text
text = ""
for item in data.get("output", []):
    if item.get("type") == "message":
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                text += c.get("text", "")

if not text.strip():
    raise RuntimeError("Model returned empty output_text. Check OpenAI model access and API key.")

payload = json.loads(text)
files = payload.get("files", {})

if not isinstance(files, dict) or not files:
    raise RuntimeError(f"Invalid 'files' returned: {payload}")

# Write files (guard paths)
allowed_prefixes = ("addons/", "AI_SPECS/")
for path, content in files.items():
    if not path.startswith(allowed_prefixes):
        raise RuntimeError(f"Blocked write outside allowed folders: {path}")

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

# Always write spec (even if model forgot)
Path(f"AI_SPECS/issue-{ISSUE_NUMBER}.md").write_text(
    f"# Issue #{ISSUE_NUMBER}\n\n## {ISSUE_TITLE}\n\n{ISSUE_BODY}\n",
    encoding="utf-8",
)
