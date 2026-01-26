import os
import json
import requests

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
ISSUE_TITLE = os.environ.get("ISSUE_TITLE", "")
ISSUE_BODY = os.environ.get("ISSUE_BODY", "")
ISSUE_NUMBER = os.environ.get("ISSUE_NUMBER", "0")

prompt = f"""
You are a senior Odoo 18 developer.

Create a minimal Odoo addon based on this issue.

STRICT RULES:
- Output VALID JSON only
- Touch ONLY addons/ and AI_SPECS/
- Structure:
  addons/ai_issue_{ISSUE_NUMBER}/
    __manifest__.py
    models/__init__.py
    models/models.py

Issue title:
{ISSUE_TITLE}

Issue body:
{ISSUE_BODY}

Return JSON with:
{{
  "files": {{
    "path/to/file": "file content"
  }}
}}
"""

response = requests.post(
    "https://api.openai.com/v1/responses",
    headers={
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": "gpt-4.1-mini",
        "input": prompt,
    },
    timeout=90,
)

response.raise_for_status()
data = response.json()

text = ""
for item in data.get("output", []):
    if item.get("type") == "message":
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                text += c.get("text", "")

payload = json.loads(text)
files = payload.get("files", {})

for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
