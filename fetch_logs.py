import urllib.request
import json
url = "https://froxy-bot-kgky.onrender.com/api/logs"
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode('utf-8'))
        logs = data.get("logs", [])
        with open("recent_render_logs.txt", "w", encoding="utf-8") as f:
            for line in logs[-50:]:
                f.write(line + "\n")
except Exception as e:
    print("Error:", e)
