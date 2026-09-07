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

endpoints = ["/api/status", "/api/group-status", "/api/stats"]

for ep in endpoints:
    url = f"{base}{ep}"
    print(f"\n--- Fetching {url} ---")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            data = json.loads(r.read().decode('utf-8'))
            print("Status Code:", r.status)
            if ep == "/api/status":
                print("Keys in /api/status:", list(data.keys()))
                print("ad_accounts:", json.dumps(data.get("ad_accounts"), indent=2, ensure_ascii=False))
                print("blast_queue:", json.dumps(data.get("blast_queue"), indent=2, ensure_ascii=False))
            elif ep == "/api/group-status":
                print("Keys in /api/group-status:", list(data.keys()))
            elif ep == "/api/stats":
                print("Stats:", json.dumps(data, indent=2, ensure_ascii=False))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"Error: {e}")
