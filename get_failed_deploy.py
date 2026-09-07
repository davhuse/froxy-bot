import urllib.request
import json
import sys

api_key = "rnd_coICmwUZglrHzzHC84glOBZTgl1U"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

svc_id = "srv-daem9k1t0dsc73ar02dg"
dep_id = "dep-dabohhe7bikc739nlstg"

# Try getting deploy logs or events
try:
    # Check if there is a logs endpoint or get deploy detail
    req = urllib.request.Request(f"https://api.render.com/v1/services/{svc_id}/deploys/{dep_id}", headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print("Deploy details:")
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Error fetching deploy detail: {e}")
