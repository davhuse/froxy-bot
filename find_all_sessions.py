import os
import re
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

found_sessions = set()

for root, dirs, files in os.walk('.'):
    if '.git' in root: continue
    for f in files:
        p = os.path.join(root, f)
        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as handle:
                text = handle.read()
                matches = re.findall(r'1[A-Za-z0-9_-]{300,400}=*', text)
                for m in matches:
                    found_sessions.add((f, m))
        except Exception:
            pass

# Also search app data dir / transcript
transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\fbd09d2b-4007-40b6-be24-bbd2f7ab73dc\.system_generated\logs\transcript_full.jsonl"
with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as handle:
    for line in handle:
        matches = re.findall(r'1[A-Za-z0-9_-]{300,400}=*', line)
        for m in matches:
            found_sessions.add(("transcript", m))

print(f"Found {len(found_sessions)} distinct Telethon string sessions!")
for fname, s in found_sessions:
    print(f"[{fname}] {s[:25]}...{s[-10:]} (len: {len(s)})")
