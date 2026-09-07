import urllib.request
import json

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

print("Testing Shopier listing creation with KeyVadi token...")
if token:
    import requests
    h = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    payload = {
        "title": "KeyVadi Test Bakiye",
        "type": "digital",
        "description": "Test",
        "stockQuantity": 1,
        "shippingPayer": "sellerPays",
        "priceData": {
            "currency": "TRY",
            "price": 10.0,
            "discount": False,
            "shippingPrice": 0.0
        },
        "media": [{"type": "image", "url": "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp/assets/keyvadi_logo.png", "placement": 1}]
    }
    r = requests.post("https://api.shopier.com/v1/products", headers=h, json=payload, timeout=10)
    print("Shopier Response Code:", r.status_code)
    print("Shopier Response Body:", r.text)
    if r.status_code in (200, 201):
        pid = r.json().get("id")
        print("Cleaning up test product:", pid)
        requests.delete(f"https://api.shopier.com/v1/products/{pid}", headers=h, timeout=5)
else:
    print("Token not found!")
