import urllib.request
import json

api_key = "rnd_coICmwUZglrHzzHC84glOBZTgl1U"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

svc_id = "srv-daem9k1t0dsc73ar02dg"

# Query logs
try:
    req = urllib.request.Request(f"https://api.render.com/v1/services/{svc_id}/logs?limit=100", headers=headers)
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode('utf-8')
        try:
            logs = json.loads(content)
            for l in logs:
                print(l.get("message", l))
        except Exception:
            print(content)
except Exception as e:
    print(f"Error fetching logs: {e}")
