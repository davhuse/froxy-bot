import re
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

log_path = r"C:\Users\habil\.gemini\antigravity\brain\99dc0ea8-66b3-483c-8a17-33763e9a7eb1\.system_generated\logs\transcript_full.jsonl"
if not os.path.exists(log_path):
    print("Full log path not found!")
    sys.exit(1)

found_keys = set()
with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if 'ad_string_session' in line:
            try:
                obj = json.loads(line)
                content = obj.get('content', '')
                # Search for any string starting with 1AZW
                keys = re.findall(r'(1AZW[a-zA-Z0-9_\-=]+)', content)
                for k in keys:
                    if len(k) > 100:
                        found_keys.add(k)
            except Exception as e:
                pass

print(f"Total unique long StringSessions found: {len(found_keys)}")
for idx, k in enumerate(sorted(list(found_keys)), 1):
    print(f"Key #{idx} (length {len(k)}): {k[:40]}...{k[-40:]}")
    # Print the full key so we can recover it
    print(f"FULL KEY: {k}\n")
