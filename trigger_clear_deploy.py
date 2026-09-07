import urllib.request
import json

api_key = "rnd_coICmwUZglrHzzHC84glOBZTgl1U"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

svc_id = "srv-daem9k1t0dsc73ar02dg"

payload = json.dumps({"clearCache": "clear"}).encode('utf-8')
req = urllib.request.Request(f"https://api.render.com/v1/services/{svc_id}/deploys", data=payload, headers=headers, method="POST")

try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print("Deploy successfully triggered:")
        print(json.dumps(data, indent=2))
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
