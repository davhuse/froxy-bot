import urllib.request
import json
url = "https://froxy-bot-kgky.onrender.com/api/logs"
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode('utf-8'))
        logs = data.get("logs", [])
        
        tracebacks = [line for line in logs if "Traceback" in line or "Exception" in line or "Error" in line]
        
        with open("recent_render_errors.txt", "w", encoding="utf-8") as f:
            for line in tracebacks[-30:]:
                f.write(line + "\n")
except Exception as e:
    print("Error:", e)
