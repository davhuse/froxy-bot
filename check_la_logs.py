import urllib.request
import json
url = "https://froxy-bot-kgky.onrender.com/api/logs"
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode('utf-8'))
        logs = data.get("logs", [])
        la_logs = [line for line in logs if "LisansArena" in line or "lisansarena" in line.lower()]
        for line in la_logs[-15:]:
            print(line.encode("ascii", errors="replace").decode("ascii"))
except Exception as e:
    print("Error:", e)
