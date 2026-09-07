import urllib.request
import json

url = "https://api.render.com/v1/services/srv-daem9k1t0dsc73ar02dg/env-vars"
headers = {
    "Authorization": "Bearer rnd_coICmwUZglrHzzHC84glOBZTgl1U",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# GET
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode('utf-8'))

new_vars = []
for item in data:
    var = item["envVar"]
    if var["key"] == "BOT_AD_ENABLED":
        var["value"] = "true"
    new_vars.append({"key": var["key"], "value": var["value"]})

# PUT
req = urllib.request.Request(url, data=json.dumps(new_vars).encode('utf-8'), headers=headers, method="PUT")
with urllib.request.urlopen(req) as r:
    print("Updated successfully!")
