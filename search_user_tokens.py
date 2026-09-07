import json

transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\fbd09d2b-4007-40b6-be24-bbd2f7ab73dc\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line_no, line in enumerate(f, 1):
        try:
            item = json.loads(line)
            if item.get("type") == "USER_INPUT":
                content = str(item.get("content", ""))
                if "eyJ" in content or "shopier" in content.lower() or "token" in content.lower():
                    print(f"--- Line {line_no} USER INPUT ---")
                    print(content[:300])
        except Exception:
            pass
