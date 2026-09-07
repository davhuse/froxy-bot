import urllib.request
import json

base_url = "https://froxy-bot-kgky.onrender.com"
endpoints = ["/api/froxy/logs", "/api/support/logs"]

with open("froxy_recent_logs.txt", "w", encoding="utf-8") as f:
    for ep in endpoints:
        f.write(f"\n--- Logs from {ep} ---\n")
        try:
            req = urllib.request.Request(base_url + ep)
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read().decode('utf-8'))
                logs = data.get("logs", [])
                for line in logs[-40:]:
                    f.write(line + "\n")
        except Exception as e:
            f.write(f"Error fetching: {e}\n")
