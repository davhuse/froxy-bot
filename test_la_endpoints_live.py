import requests
import json

BASE = "https://bot-service-production-9d74.up.railway.app/la/app"

print("--- 1. Testing GET /api/products ---")
r = requests.get(f"{BASE}/api/products")
print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"Total products: {data.get('count')}")
    sample = data.get('products', [])[:2]
    for p in sample:
        print(f"  {p.get('id')}: {p.get('title')} | {p.get('price')} | Shopier: {p.get('shopier_url')}")
else:
    print(r.text)

print("\n--- 2. Testing user auth without Telegram Init Data ---")
r = requests.get(f"{BASE}/api/user/123456789")
print(f"GET /api/user/123456789 -> {r.status_code}: {r.text}")

print("\n--- 3. Testing create-dynamic-topup without auth ---")
r = requests.post(f"{BASE}/api/balance/create-dynamic-topup", json={"amount": 50})
print(f"POST /api/balance/create-dynamic-topup -> {r.status_code}: {r.text}")
