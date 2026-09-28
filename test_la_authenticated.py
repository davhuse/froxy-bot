import hmac, hashlib, time, json, urllib.parse, requests

BOT_TOKEN = "8971644903:AAGYnF338b9sV5b-W4vO_nFw9q6mD5e3z-8" # Wait, let's get from Railway vars

# Fetch real token from Railway
from check_shopier_jwts import vars
bot_token = vars.get("LISANSARENA_BOT_TOKEN")

user_data = {
    "id": 123456789,
    "first_name": "Habil",
    "last_name": "Test",
    "username": "habiltest",
    "language_code": "tr"
}

params = {
    "auth_date": str(int(time.time())),
    "query_id": "AAHdF6IQAAAAAN0XohD12345",
    "user": json.dumps(user_data, separators=(',', ':'))
}

data_check_string = "\n".join(f"{k}={params[k]}" for k in sorted(params.keys()))
secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
params["hash"] = calculated_hash

init_data = urllib.parse.urlencode(params)
print("Generated valid init_data:", init_data[:50], "...")

BASE = "https://bot-service-production-9d74.up.railway.app/la/app"
headers = {
    "X-Telegram-Init-Data": init_data,
    "Content-Type": "application/json"
}

print("\n--- 1. Testing GET /api/user/123456789 ---")
r = requests.get(f"{BASE}/api/user/123456789", headers=headers)
print(f"Status: {r.status_code}, Response: {r.text}")

print("\n--- 2. Testing POST /api/balance/create-dynamic-topup (Wallet Topup) ---")
r2 = requests.post(f"{BASE}/api/balance/create-dynamic-topup", headers=headers, json={"amount": 50})
print(f"Status: {r2.status_code}, Response: {r2.text}")
data2 = r2.json()
if data2.get("product_id"):
    # Cancel and clean up
    c_res = requests.post(f"{BASE}/api/balance/cancel-topup", headers=headers, json={"product_id": data2["product_id"]})
    print(f"Cleanup Topup 1: {c_res.status_code}, {c_res.text}")

print("\n--- 3. Testing POST /api/balance/create-dynamic-topup (Direct Product Purchase) ---")
r3 = requests.post(f"{BASE}/api/balance/create-dynamic-topup", headers=headers, json={
    "amount": 599.90,
    "product_title": "Adobe Express 12 Ay",
    "product_id": "la_adobe_express_12_personal"
})
print(f"Status: {r3.status_code}, Response: {r3.text}")
data3 = r3.json()
if data3.get("product_id"):
    c_res = requests.post(f"{BASE}/api/balance/cancel-topup", headers=headers, json={"product_id": data3["product_id"]})
    print(f"Cleanup Topup 2: {c_res.status_code}, {c_res.text}")

print("\n--- 4. Testing POST /api/user/purchase with 0 balance ---")
r4 = requests.post(f"{BASE}/api/user/purchase", headers=headers, json={
    "product_id": "la_adobe_express_12_personal",
    "idempotency_key": "test_purchase_1"
})
print(f"Status: {r4.status_code}, Response: {r4.text}")

print("\n--- 5. Testing GET /api/products ---")
r5 = requests.get(f"{BASE}/api/products")
products_data = r5.json().get("products", [])
print(f"Products count: {len(products_data)}")
if products_data:
    p0 = products_data[0]
    print(f"Sample product: {p0.get('title')}")
    print(f"  URL: {p0.get('url')}")
    print(f"  price_num: {p0.get('price_num')}")
    print(f"  description length: {len(p0.get('description', ''))}")

