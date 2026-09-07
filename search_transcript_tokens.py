import json
import re

transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\fbd09d2b-4007-40b6-be24-bbd2f7ab73dc\.system_generated\logs\transcript_full.jsonl"

found_tokens = []
with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line_no, line in enumerate(f, 1):
        if 'eyJ' in line:
            matches = re.findall(r'eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}', line)
            for m in matches:
                found_tokens.append((line_no, m))

print(f"Total tokens found in transcript: {len(found_tokens)}")
for line_no, t in set(found_tokens):
    print(f"Line {line_no}: {t[:20]}...{t[-15:]} (len: {len(t)})")
