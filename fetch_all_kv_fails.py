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

req = urllib.request.Request(f"{base}/api/logs?limit=500", headers=headers)
with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
    logs = json.loads(r.read().decode('utf-8')).get("logs", [])
    fails = [l for l in logs if "KeyVadiOnline" in l and any(w in l for w in ["❌", "🔒", "🚫", "⚠️"])]
    print(f"Total KeyVadi issues in recent logs: {len(fails)}")
    for f in fails:
        print(" ", f.strip())
