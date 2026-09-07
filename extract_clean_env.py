import json
import re
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\fbd09d2b-4007-40b6-be24-bbd2f7ab73dc\.system_generated\logs\transcript_full.jsonl"

all_env = {}

with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line_no, line in enumerate(f, 1):
        if "srv-da" in line and ("env-vars" in line or "envVar" in line):
            # Check if line contains a JSON array of env vars
            try:
                # Find occurrences of [{ "envVar": ... }] or [{ "key": ... }]
                idx = line.find('[{"')
                if idx != -1:
                    end_idx = line.rfind('}]')
                    if end_idx != -1:
                        chunk = line[idx:end_idx+2]
                        # Fix escaped quotes if any
                        chunk_unescaped = chunk.replace('\\"', '"').replace('\\\\', '\\')
                        try:
                            parsed = json.loads(chunk_unescaped)
                            if isinstance(parsed, list):
                                for item in parsed:
                                    if "envVar" in item:
                                        k = item["envVar"]["key"]
                                        v = item["envVar"]["value"]
                                        all_env[k] = v
                                    elif "key" in item and "value" in item:
                                        k = item["key"]
                                        v = item["value"]
                                        all_env[k] = v
                        except Exception:
                            pass
            except Exception:
                pass

print(f"Extracted {len(all_env)} clean environment variables:")
for k, v in all_env.items():
    masked = v[:8] + "..." + v[-4:] if len(v) > 12 else v
    print(f"  {k} = {masked} (len: {len(v)})")
