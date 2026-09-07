import urllib.request
import json
url = "https://froxy-bot-kgky.onrender.com/api/config"
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode('utf-8'))
        print("Froxy running:", data.get("froxy_bot_running"))
        print("Support running:", data.get("support_bot_running"))
except Exception as e:
    print("Error:", e)
