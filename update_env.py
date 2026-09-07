import urllib.request
import json

url = "https://api.render.com/v1/services/srv-daem9k1t0dsc73ar02dg/env-vars"
headers = {
    "Authorization": "Bearer rnd_coICmwUZglrHzzHC84glOBZTgl1U",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# First, GET all existing env vars
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode('utf-8'))

# Update the specific ones
new_vars = []
for item in data:
    var = item["envVar"]
    if var["key"] == "LISANSARENA_MINI_APP_URL":
        var["value"] = "https://froxy-bot-kgky.onrender.com/la/app"
    
    # We must only send key/value in the array
    new_vars.append({
        "key": var["key"],
        "value": var["value"]
    })

# PUT the updated array back
req = urllib.request.Request(url, data=json.dumps(new_vars).encode('utf-8'), headers=headers, method="PUT")
with urllib.request.urlopen(req) as r:
    print(r.read().decode('utf-8'))
