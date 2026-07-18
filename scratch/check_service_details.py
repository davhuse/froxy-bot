import json
import urllib.request
import urllib.error

RENDER_API_KEY = "rnd_uSYeDJkX0xrcNfgo2BP7Tu3dRvuE"
SERVICE_ID = "srv-d8ecii58nd3s73afm620" # froxy-bot

def make_request(url, method="GET", headers=None, data=None):
    if headers is None:
        headers = {}
    
    req = urllib.request.Request(url, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
        
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode("utf-8")), None
    except Exception as e:
        return None, str(e)

headers = {
    "Authorization": f"Bearer {RENDER_API_KEY}",
    "Accept": "application/json"
}

res, _ = make_request(f"https://api.render.com/v1/services/{SERVICE_ID}", headers=headers)
if res:
    print(json.dumps(res, indent=2))
else:
    print("Failed to get service details")
