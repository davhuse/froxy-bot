import json
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\fbd09d2b-4007-40b6-be24-bbd2f7ab73dc\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line_no, line in enumerate(f, 1):
        if line_no < 7600:
            if "FIREBASE_API_KEY" in line or "SHOPIER_KEYVADI_ACCESS_TOKEN" in line:
                print(f"Line {line_no}: len={len(line)}")
                try:
                    obj = json.loads(line)
                    c = json.dumps(obj)
                    for k in ["FIREBASE_API_KEY", "FIREBASE_PROJECT_ID", "SHOPIER_KEYVADI_ACCESS_TOKEN", "AD_STRING_SESSION_KEYVADI", "AD_STRING_SESSION_FROXY", "AD_STRING_SESSION_LISANSARENA"]:
                        pos = c.find(k)
                        if pos != -1:
                            print(f"  {k} snippet: {c[pos:pos+150]}")
                except Exception as e:
                    print("  JSON parse error:", e)
