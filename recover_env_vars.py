import json
import re

transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\fbd09d2b-4007-40b6-be24-bbd2f7ab73dc\.system_generated\logs\transcript_full.jsonl"

found_vars = {}

# Search for complete env vars payloads in transcript
with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if "SHOPIER_KEYVADI_ACCESS_TOKEN" in line or "AD_STRING_SESSION_FROXY" in line or "FIREBASE_API_KEY" in line:
            # Look for JSON arrays or dicts containing key/value
            try:
                # Find all occurrences of "key": "...", "value": "..."
                matches = re.findall(r'"key":\s*"([^"]+)",\s*"value":\s*"([^"]+)"', line)
                for k, v in matches:
                    if k not in found_vars or len(v) > len(found_vars[k]):
                        found_vars[k] = v
            except Exception:
                pass

print(f"Found {len(found_vars)} environment variables in transcript:")
for k, v in found_vars.items():
    masked = v[:6] + "..." + v[-4:] if len(v) > 10 else v
    print(f"  {k} = {masked}")
