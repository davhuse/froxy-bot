import json
import re
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\fbd09d2b-4007-40b6-be24-bbd2f7ab73dc\.system_generated\logs\transcript_full.jsonl"

missing_keys = [
    "FIREBASE_API_KEY",
    "FIREBASE_PROJECT_ID",
    "SHOPIER_KEYVADI_ACCESS_TOKEN",
    "SHOPIER_FROXY_ACCESS_TOKEN",
    "AD_STRING_SESSION_FROXY",
    "AD_STRING_SESSION_KEYVADI",
    "AD_STRING_SESSION_LISANSARENA"
]

found = {}

with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line_no, line in enumerate(f, 1):
        for k in missing_keys:
            if k in line:
                # Find all potential matches
                for m in re.finditer(rf'["\']?{k}["\']?\s*[:=]\s*["\']([^"\'\r\n\\]+)["\']', line):
                    val = m.group(1).strip()
                    if not val.startswith("...") and not val.endswith("...") and val != "***":
                        if k not in found or len(val) > len(found[k]):
                            found[k] = val

print("=== SPECIFIC KEYS FOUND ===")
for k in missing_keys:
    val = found.get(k)
    if val:
        print(f"  {k} = {val[:12]}...{val[-6:]} (len: {len(val)})")
    else:
        print(f"  ❌ {k} not matched with regex, searching broadly...")
