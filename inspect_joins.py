import urllib.request
import json

url = "https://froxy-bot-kgky.onrender.com/api/logs"
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode('utf-8'))
logs = data.get("logs", [])

for line in logs:
    if "katıl" in line.lower() or "istek" in line.lower() or "bekleniyor" in line.lower():
        if "KeyVadi" in line or "Froxy" in line:
            print(line.encode("ascii", errors="replace").decode("ascii"))
