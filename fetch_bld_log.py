import urllib.request
import json

api_key = "rnd_coICmwUZglrHzzHC84glOBZTgl1U"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

svc_id = "srv-daem9k1t0dsc73ar02dg"

# List deploys
d_req = urllib.request.Request(f"https://api.render.com/v1/services/{svc_id}/deploys?limit=1", headers=headers)
with urllib.request.urlopen(d_req) as resp:
    deploys = json.loads(resp.read().decode('utf-8'))
    dep = deploys[0]["deploy"]
    print("Latest Deploy:", dep["id"], dep["status"])

# Try getting logs for service
# Render logs API: GET /v1/services/{serviceId}/logs or similar or /v1/services/{serviceId}/deploys/{deployId}/events
