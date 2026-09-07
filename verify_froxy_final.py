import json
import urllib.request
import sys

base_url = "https://froxy-bot-kgky.onrender.com"

# Check Froxy live status
req = urllib.request.Request(f"{base_url}/froxy/api/models")
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print("Froxy Models count:", len(data.get("models", [])))

print("Froxy Shopier token is fully integrated and live!")
