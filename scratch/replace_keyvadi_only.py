import urllib.request
import urllib.error
import json
import ssl
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Exact, uncorrupted KeyVadi token from Habil
token_kv = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJiOGI0MjA0NWM1NDY2ZDdiMWQwODc0OGUzZTBkNDlmNSIsImp0aSI6IjllZDI4ZTU3ZjZkOTFjOWFjZTRjN2Y0YzNhZmUyZjg3YTg0NWEyZDAxNzdiNDgxZTlkNWE2OTAwZTY4YjVkYzliN2UxY2UwNmQ4YzYxZjQ3YTA2ZWJkOGEyMGJhMGNlMTM3ZDFjNDI0N2VhNGQzNzNhYzQ4YTFhYzBhZDIxOGM1YzVkZWM1ZGNiOTlkNjdlM2M5NTJjYjFjMWU5ZjlmZjMiLCJpYXQiOjE3ODQxMjIzODIsIm5iZiI6MTc4NDEyMjM4MiwiZXhwIjoxOTQxOTA3MTQyLCJzdWIiOjI1MDk0OTMsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.jdLI_JWWU1MlRz4A4vxKj0EtfeffmuJFzO8Eq3YC2aWiY1MFEZZ8x6HQdSiqdB3JY1U4Sirk8cVfysm1FU9ulCtrtcviPztPQWWGL0AGgbqRDlc2uw4YhuPzLIIafA_Ej1O_BIDI48UOK6LpvBWapMjISa23Jjj5MLISvYRH9lMS_v2IUDpjvsf-6H6Bpi1BCNvSlLoMRT8_SPnqPY3908zsm3xZvPfENBQAtpdvydAdFVtq-EaNesit5gWER8NaUickGDZ7_G7KOdF-08Ej4YOAxly_HvWaO8Gi_JzKqYnMgd66d-snGOpj0pIvsqKmRmdHJ53tflFF_X363dKaBg"

to_delete_kv = []

new_products = [
    {
        "title": "HBO Max 1 Aylık Profil",
        "price": 39.90,
        "desc": "HBO Max 1 Aylık Premium Profil. Size özel profil ismi ve şifreleme sağlanır.",
        "image_url": "https://veridia-bot.onrender.com/static/la_hbo.png"
    },
    {
        "title": "Prime Video (1 Aylık) - Özel Profil",
        "price": 29.90,
        "desc": "Amazon Prime Video 1 Aylık Kişisel Profil. Özel şifreli profil ile kesintisiz izleme.",
        "image_url": "https://veridia-bot.onrender.com/static/la_prime.png"
    },
    {
        "title": "Prime Video (1 Aylık) - Ortak Profil",
        "price": 19.90,
        "desc": "Amazon Prime Video 1 Aylık Ortak Kullanım Hesabı. Giriş garantilidir.",
        "image_url": "https://veridia-bot.onrender.com/static/la_prime.png"
    }
]

# 1. Delete temporary KeyVadi products
print("--- Deleting temporary KeyVadi products ---")
headers = {
    "User-Agent": "Mozilla/5.0",
    "Authorization": f"Bearer {token_kv}",
    "Accept": "application/json"
}
for pid in to_delete_kv:
    url = f"https://api.shopier.com/v1/products/{pid}"
    req = urllib.request.Request(url, headers=headers, method="DELETE")
    print(f"Deleting product {pid}...")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            print("  [SUCCESS] Deleted.")
    except Exception as e:
        print(f"  [FAILED] Error: {e}")
    time.sleep(1.5)

# 2. Create products with correct mockups
print("\n--- Creating products for KeyVadi ---")
url = "https://api.shopier.com/v1/products"
results = []

for idx, p in enumerate(new_products):
    payload = {
        "title": p["title"],
        "description": p["desc"],
        "type": "digital",
        "media": [
            {
                "type": "image",
                "url": p["image_url"],
                "placement": 1
            }
        ],
        "priceData": {
            "currency": "TRY",
            "price": f"{p['price']:.2f}",
            "discount": False,
            "discountedPrice": f"{p['price']:.2f}",
            "shippingPrice": "0.00"
        },
        "stockQuantity": 999,
        "shippingPayer": "sellerPays"
    }
    
    headers_post = {
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"Bearer {token_kv}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers_post, method="POST")
    print(f"[{idx+1}/{len(new_products)}] Creating: {p['title']} ({p['price']} TL)...")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            res = json.loads(r.read().decode("utf-8"))
            pid = res.get("id")
            purl = res.get("url")
            print(f"  [SUCCESS] Product ID: {pid} | URL: {purl}")
            slug = "hbo_max" if "HBO" in p["title"] else ("prime_video_ozel" if "Özel" in p["title"] else "prime_video_ortak")
            results.append({
                "slug": slug,
                "id": pid,
                "url": purl,
                "title": p["title"],
                "price": f"{p['price']:.2f}"
            })
    except urllib.error.HTTPError as e:
        print(f"  [FAILED] HTTP Error {e.code}: {e.reason}")
        try:
            print("  Response Body:", e.read().decode("utf-8"))
        except:
            pass
    except Exception as e:
        print(f"  [FAILED] Other error: {e}")
    time.sleep(2.0)

print("\nFinished KeyVadi creations:")
for r in results:
    print(f"Slug: {r['slug']} | New ID: {r['id']} | URL: {r['url']}")
    
with open("keyvadi_new_ids.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
