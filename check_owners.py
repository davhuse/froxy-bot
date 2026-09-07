import urllib.request
import json

api_key = "rnd_coICmwUZglrHzzHC84glOBZTgl1U"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

try:
    req = urllib.request.Request("https://api.render.com/v1/owners", headers=headers)
    with urllib.request.urlopen(req) as resp:
        owners = json.loads(resp.read().decode('utf-8'))
        print("Owners:")
        print(json.dumps(owners, indent=2))
except Exception as e:
    print("Error:", e)
