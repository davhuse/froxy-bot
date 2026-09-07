import json
import re
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\fbd09d2b-4007-40b6-be24-bbd2f7ab73dc\.system_generated\logs\transcript_full.jsonl"

all_env = {}

with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line_no, line in enumerate(f, 1):
        if "env-vars" in line or "envVar" in line or "AD_STRING_SESSION" in line:
            try:
                row = json.loads(line)
                content = str(row.get("content") or "") + str(row.get("tool_calls") or "")
                # Find all occurrences of {"key": "...", "value": "..."} or {"envVar": {"key": "...", "value": "..."}}
                # Regex for envVar key-value
                for m in re.finditer(r'["\']key["\']\s*:\s*["\']([^"\']+)["\'],\s*["\']value["\']\s*:\s*["\']([^"\']+)["\']', content):
                    k, v = m.group(1), m.group(2)
                    if k not in all_env or len(v) > len(all_env[k]):
                        all_env[k] = v
                for m in re.finditer(r'["\']envVar["\']\s*:\s*\{[^}]*["\']key["\']\s*:\s*["\']([^"\']+)["\'],\s*["\']value["\']\s*:\s*["\']([^"\']+)["\']', content):
                    k, v = m.group(1), m.group(2)
                    if k not in all_env or len(v) > len(all_env[k]):
                        all_env[k] = v
            except Exception:
                pass

print(f"Extracted {len(all_env)} clean environment variables:")
for k, v in all_env.items():
    masked = v[:8] + "..." + v[-4:] if len(v) > 12 else v
    print(f"  {k} = {masked} (len: {len(v)})")
