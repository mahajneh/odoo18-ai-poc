import os, json, requests
from pathlib import Path

print("=== AI GENERATOR v2 (DEBUG) ===")  # <-- signature

key = os.environ.get("OPENAI_API_KEY", "")
if not key:
    raise RuntimeError("OPENAI_API_KEY missing in GitHub Secrets.")

issue_title = os.environ.get("ISSUE_TITLE", "")
issue_body = os.environ.get("ISSUE_BODY", "")
issue_number = os.environ.get("ISSUE_NUMBER", "0")

Path("addons").mkdir(exist_ok=True)
Path("AI_SPECS").mkdir(exist_ok=True)

prompt = f"""
Return ONLY valid JSON in this format:
{{
  "files": {{
    "addons/ai_issue_{issue_number}/__manifest__.py": "...",
    "addons/ai_issue_{issue_number}/models/__init__.py": "...",
    "addons/ai_issue_{issue_number}/models/models.py": "..."
  }}
}}
No markdown. No explanations.

Issue title: {issue_title}
Issue body: {issue_body}
"""

r = requests.post(
    "https://api.openai.com/v1/responses",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={"model": "gpt-4o-mini", "input": prompt},
    timeout=120,
)

print("OpenAI status:", r.status_code)
print("OpenAI raw response:", r.text[:2000])  # print first 2k chars

if r.status_code >= 400:
    raise RuntimeError(f"OpenAI API error {r.status_code}")

data = r.json()

text = ""
for item in data.get("output", []):
    if item.get("type") == "message":
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                text += c.get("text", "")

print("Extracted output_text (first 2000 chars):", text[:2000])

payload = json.loads(text)
files = payload.get("files", {})

for path, content in files.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

Path(f"AI_SPECS/issue-{issue_number}.md").write_text(
    f"# Issue #{issue_number}\n\n## {issue_title}\n\n{issue_body}\n", encoding="utf-8"
)
