import urllib.request
import json

api_key = "rnd_coICmwUZglrHzzHC84glOBZTgl1U"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

svc_id = "srv-daem9k1t0dsc73ar02dg"
dep_id = "dep-dabohhe7bikc739nlstg"

# Try getting events or logs
for endpoint in [
    f"https://api.render.com/v1/services/{svc_id}/deploys/{dep_id}/events",
    f"https://api.render.com/v1/services/{svc_id}/events",
]:
    try:
        req = urllib.request.Request(endpoint, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"=== {endpoint} ===")
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error {endpoint}: {e}")
