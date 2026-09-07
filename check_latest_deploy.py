import urllib.request
import json

api_key = "rnd_coICmwUZglrHzzHC84glOBZTgl1U"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

svc_id = "srv-daem9k1t0dsc73ar02dg"

req = urllib.request.Request(f"https://api.render.com/v1/services/{svc_id}/deploys?limit=1", headers=headers)
with urllib.request.urlopen(req) as resp:
    deploys = json.loads(resp.read().decode('utf-8'))
    dep = deploys[0]["deploy"]
    print(f"Deploy ID: {dep['id']} | Status: {dep['status']}")
