import json
import re
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\fbd09d2b-4007-40b6-be24-bbd2f7ab73dc\.system_generated\logs\transcript_full.jsonl"

keys_to_find = [
    "AD_STRING_SESSION_FROXY",
    "AD_STRING_SESSION_LISANSARENA",
    "AD_STRING_SESSION_KEYVADI",
    "FIREBASE_API_KEY",
    "FIREBASE_PROJECT_ID",
    "KEYVADI_SUPPORT_BOT_TOKEN",
    "LISANSARENA_BOT_TOKEN",
    "FROXY_SUPPORT_BOT_TOKEN",
    "PANEL_ADMIN_TOKEN",
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "TELEGRAM_ADMIN_ID",
    "FLASK_SECRET_KEY",
    "LISANSARENA_DATABASE_URL",
    "LISANSARENA_STOCK_KEY",
    "LISANSARENA_SHOPIER_WEBHOOK_SECRET",
    "SHOPIER_KEYVADI_ACCESS_TOKEN",
    "SHOPIER_LISANSARENA_ACCESS_TOKEN",
    "SHOPIER_FROXY_ACCESS_TOKEN"
]

results = {}

with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line_no, line in enumerate(f, 1):
        for k in keys_to_find:
            # Look for patterns like key = "..." or "key": "..." or 'key': '...'
            patterns = [
                rf'["\']?{k}["\']?\s*[:=]\s*["\']([^"\'\r\n]+)["\']',
                rf'{k}\s*=\s*([^\s\r\n,]+)',
                rf'["\']{k}["\']\s*:\s*["\']([^"\']+)["\']'
            ]
            for p in patterns:
                m = re.search(p, line)
                if m:
                    val = m.group(1).strip()
                    if not val.startswith("...") and not val.endswith("...") and val != "***":
                        if k not in results or len(val) > len(results[k]):
                            results[k] = val

print("=== RECOVERED ENV VARS ===")
for k in keys_to_find:
    val = results.get(k)
    if val:
        print(f"  {k} = {val[:10]}...{val[-6:]} (len: {len(val)})")
    else:
        print(f"  ❌ {k} NOT FOUND!")
