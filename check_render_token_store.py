import urllib.request
import json
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

api_key = "rnd_coICmwUZglrHzzHC84glOBZTgl1U"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

svc_id = "srv-daem9k1t0dsc73ar02dg"

req = urllib.request.Request(f"https://api.render.com/v1/services/{svc_id}/env-vars", headers=headers)
with urllib.request.urlopen(req) as resp:
    env_vars = json.loads(resp.read().decode('utf-8'))
    token = None
    for item in env_vars:
        ev = item.get("envVar", {})
        if ev.get("key") == "SHOPIER_KEYVADI_ACCESS_TOKEN":
            token = ev.get("value")
            break

if token:
    import requests
    h = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    r = requests.get("https://api.shopier.com/v1/products?limit=5", headers=h, timeout=10)
    print("Status:", r.status_code)
    if r.status_code == 200:
        for p in r.json():
            print("Product:", p.get("title"), "| URL:", p.get("url"))
