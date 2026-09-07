import json

transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\fbd09d2b-4007-40b6-be24-bbd2f7ab73dc\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line_no, line in enumerate(f, 1):
        if "AD_STRING_SESSION_FROXY" in line:
            print(f"Line {line_no} has AD_STRING_SESSION_FROXY (length: {len(line)})")
            try:
                item = json.loads(line)
                content = str(item.get("content") or "")
                print("Content preview:", content[:500])
            except Exception as e:
                print("JSON error:", e)
