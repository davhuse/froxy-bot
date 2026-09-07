import urllib.request
import json
url = "https://api.render.com/v1/services/srv-daem9k1t0dsc73ar02dg/env-vars"
headers = {
    "Authorization": "Bearer rnd_coICmwUZglrHzzHC84glOBZTgl1U",
    "Accept": "application/json"
}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode('utf-8'))
for item in data:
    if "DISABLED_AD_ACCOUNTS" in item['envVar']['key']:
        print(f"{item['envVar']['key']} = '{item['envVar']['value']}'")
