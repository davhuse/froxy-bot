import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

endpoints = ["/api/logs", "/api/support/logs", "/api/froxy/logs", "/api/tickets"]
base_url = "https://froxy-bot-kgky.onrender.com"

for ep in endpoints:
    try:
        req = urllib.request.Request(base_url + ep)
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode('utf-8'))
            print(f"=== {ep} ===")
            if ep == "/api/tickets":
                tickets = data.get("tickets", [])
                matches = [t for t in tickets if "polat" in str(t).lower()]
                for m in matches:
                    print(m)
            else:
                logs = data.get("logs", [])
                matches = [l for l in logs if "polat" in str(l).lower()]
                for m in matches:
                    print(m)
    except Exception as e:
        print(f"Error {ep}: {e}")
