import urllib.request
import json
import ssl
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = "https://froxy-bot-kgky.onrender.com"
token = "VOJVbVkVHQBw5J3zI8vQeW2zP5iK6uY9"
headers = {
    "X-Admin-Token": token,
    "User-Agent": "Mozilla/5.0"
}

try:
    req = urllib.request.Request(f"{base}/api/logs?limit=200", headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        logs_data = json.loads(r.read().decode('utf-8'))
        logs = logs_data.get("logs", [])
        print(f"Fetched {len(logs)} log lines. Filtering for KeyVadi...")
        kv_logs = [l for l in logs if "KeyVadi" in l or "keyvadi" in l.lower()]
        for l in kv_logs[-40:]:
            print(" ", l.strip())
except Exception as e:
    print("Error:", e)
