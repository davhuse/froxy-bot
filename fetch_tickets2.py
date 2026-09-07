import urllib.request
import json
url = "https://froxy-bot-kgky.onrender.com/api/tickets"
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode('utf-8'))
        tickets = data.get("tickets", [])
        for t in tickets:
            if t.get('bot_type') == 'Froxy AI':
                print(f"[{t.get('bot_type')}] User {t.get('user_id')} (@{t.get('username')}): {t.get('message')}")
except Exception as e:
    print("Error:", e)
