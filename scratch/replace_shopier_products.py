import urllib.request
import urllib.error
import json
import ssl
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Exact active tokens
token_kv = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJiOGI0MjA0NWM1NDY2ZDdiMWQwODc0OGUzZTBkNDlmNSIsImp0aSI6IjllZDI4ZTU3ZjZkOTFjOWFjZTRjN2Y0YzNhZmUyZjg3YTg0NWEyZDAxNzdiNDgxZTlkNWE2OTAwZTY4YjVkYzliN2UxY2UwNmQ4YzYxZjQ3YTA2ZWJkOGEyMGJhMGNlMTM3ZDFjNDI0N2VhNGQzNzNhYzQ4YTFhYzBhZDIxOGM1YzVkZWM1ZGNiOTlkNjdlM2M5NTJjYjFjMWU5ZjlmZjMiLCJpYXQiOjE3ODQxMjIzODIsIm5iZiI6MTc4NDEyMjM4MiwiZXhwIjoxOTQxOTA3MTQyLCJzdWIiOjI5ODgwNTAsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.jdLI_JWWU1MlRz4A4vxKj0EtfeffmuJFzO8Eq3YC2aWiY1MFEZZ8x6HQdSiqdB3JY1U4Sirk8cVfysm1FU9ulCtrtcviPztPQWWGL0AGgbqRDlc2uw4YhuPzLIIafA_Ej1O_BIDI48UOK6LpvBWapMjISa23Jjj5MLISvYRH9lMS_v2IUDpjvsf-6H6Bpi1BCNvSlLoMRT8_SPnqPY3908zsm3xZvPfENBQAtpdvydAdFVtq-EaNesit5gWER8NaUickGDZ7_G7KOdF-08Ej4YOAxly_HvWaO8Gi_JzKqYnMgd66d-snGOpj0pIvsqKmRmdHJ53tflFF_X363dKaBg"
token_la = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5YjI5OWVmNzFlNTYyNDIzNDIxYTk5NDc1YzA2YWVlNiIsImp0aSI6IjkyMjYyZGFlMjliZmFkY2NhYTA1OTRmZWQ1NDg3MzQyMjA4ZTY0OGZhMTI4ZjFiYzI1OWQ1ZDI5NDczODc2ZWM0OTU2MjkyOWM3ODE4MWJjMGE1ZGIxMTNlODM3NTRmODVhNTEzNDQwMjU5YjVkNDU0N2M0YTgyZDNlMjI4ZTVmMjRkZjhhNTQ4NDQ5NGNlYzIxYjg1N2UxYWRmMmY2OWMiLCJpYXQiOjE3ODM4MDk2OTUsIm5iZiI6MTc4MzgwOTY5NSwiZXhwIjoxOTQxNTk0NDU1LCJzdWIiOjI5ODgwNTAsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.bMbTumHi1Jzjl49eZbNfY-S8X7zAYvpnPNOpLxv2RAm76ZcHJbtj_9QrCYL6Q679vtyA2SdB8vdhXmTtVRi4t7PO63Q1LDN4BQTxY5ZbxbBFrVdbkUi-9GC7QXuDcooxOuI8WC6CBqXr9pCyK3Hx-N8QCldTpmz54Hv9iyL0Y4t0ZLZ-F_-V_vWli9qTcMEODqsg-eC-dNgrqKVwdJjrQqWlMK60nNliYlTzxWJmYVjp0jmHHx6sQWRQNDy1Iu39sZefbFHqQKEJt77icupETH_-Y3h1cwSvv9aMh-kSndNrP-dYFSp6B3yWAXo6KhB19dK9HOHk-NGJNL4v4e13lQ"

# Temporary products to delete
to_delete_kv = ["49000411", "49000412", "49000414"]
to_delete_la = ["49000419", "49000421", "49000422"]

# Products to create
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

def delete_products(token, ids, store_name):
    print(f"\n--- Deleting products for {store_name} ---")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    for pid in ids:
        url = f"https://api.shopier.com/v1/products/{pid}"
        req = urllib.request.Request(url, headers=headers, method="DELETE")
        print(f"Deleting product {pid}...")
        try:
            with urllib.request.urlopen(req, context=ctx) as r:
                print("  [SUCCESS] Deleted.")
        except Exception as e:
            print(f"  [FAILED] Error: {e}")
        time.sleep(1.5)

def create_products(token, store_name):
    print(f"\n--- Creating products for {store_name} ---")
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
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
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
    return results

# 1. Delete old temporary products
delete_products(token_kv, to_delete_kv, "KeyVadi")
delete_products(token_la, to_delete_la, "LisansArena")

# 2. Create products with correct mockups
kv_created = create_products(token_kv, "KeyVadi")
la_created = create_products(token_la, "LisansArena")

# Save results to integrate
out = {
    "KeyVadi": kv_created,
    "LisansArena": la_created
}

with open("uploaded_products_results_final.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("\nProduct replacement complete. Results written to uploaded_products_results_final.json")
