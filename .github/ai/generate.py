import os
import json
import requests
from pathlib import Path

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
ISSUE_TITLE = os.environ.get("ISSUE_TITLE", "")
ISSUE_BODY = os.environ.get("ISSUE_BODY", "")
ISSUE_NUMBER = os.environ.get("ISSUE_NUMBER", "0")

# Only allow writing here
ALLOWED_PREFIXES = ("addons/", "AI_SPECS/")

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

prompt = f"""
You are a senior Odoo 18 developer.

Create a minimal Odoo addon based on this issue.

Rules:
- Create addon in: addons/ai_issue_{ISSUE_NUMBER}/
- Include at least:
  - __manifest__.py
  - models/__init__.py
  - models/models.py
- Keep files minimal but valid.
"""

issue = f"TITLE: {ISSUE_TITLE}\n\nBODY:\n{ISSUE_BODY}"

resp = requests.post(
    "https://api.openai.com/v1/responses",
    headers={
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": "gpt-4o-mini",  # safer default availability
        "input": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": issue},
        ],
        # Force JSON output
        "text": {"format": {"type": "json_schema", "json_schema": schema}},
    },
    timeout=120,
)

# If OpenAI returns an error, show it in logs
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
    raise RuntimeError("Model returned empty output_text. Check model access / API key / response payload.")

# Parse strictly
payload = json.loads(text)
files = payload.get("files", {})

if not isinstance(files, dict) or not files:
    raise RuntimeError(f"Invalid 'files' object returned: {payload}")

# Write files (with path guard)
for path, content in files.items():
    if not any(path.startswith(p) for p in ALLOWED_PREFIXES):
        raise RuntimeError(f"Blocked path outside allowed prefixes: {path}")

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

# Write a simple spec trace
Path("AI_SPECS").mkdir(exist_ok=True)
Path(f"AI_SPECS/issue-{ISSUE_NUMBER}.md").write_text(
    f"# Issue #{ISSUE_NUMBER}\n\n## {ISSUE_TITLE}\n\n{ISSUE_BODY}\n",
    encoding="utf-8",
)
