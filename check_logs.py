import urllib.request
import json

base_url = "https://froxy-bot-kgky.onrender.com"
endpoints = ["/api/logs", "/api/froxy/logs"]

for ep in endpoints:
    print(f"\n--- Logs from {ep} ---")
    try:
        req = urllib.request.Request(base_url + ep)
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode('utf-8'))
            logs = data.get("logs", [])
            for line in logs[-15:]:
                print(line)
    except Exception as e:
        print("Error fetching:", e)
