import urllib.request
import json
import sys

api_key = "rnd_coICmwUZglrHzzHC84glOBZTgl1U"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

svc_id = "srv-daem9k1t0dsc73ar02dg"

try:
    # Render API: GET /v1/services/{serviceId}/logs or deconstruct deploy logs
    # Note: list deploys or check service info
    req = urllib.request.Request(f"https://api.render.com/v1/services/{svc_id}/deploys?limit=5", headers=headers)
    with urllib.request.urlopen(req) as resp:
        deploys = json.loads(resp.read().decode('utf-8'))
        print("=== RECENT DEPLOYS ===")
        for d in deploys:
            dep = d.get("deploy", {})
            print(f"Deploy: {dep.get('id')} | Status: {dep.get('status')} | Commit: {dep.get('commit', {}).get('message', '')[:60]} | Finished: {dep.get('finishedAt')}")
except Exception as e:
    print("Error fetching deploys:", e)
