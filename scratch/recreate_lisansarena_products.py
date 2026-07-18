import urllib.request
import urllib.error
import json
import ssl
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Correct working token (from create_target_lisansarena_products.py)
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5YjI5OWVmNzFlNTYyNDIzNDIxYTk5NDc1YzA2YWVlNiIsImp0aSI6IjkyMjYyZGFlMjliZmFkY2NhYTA1OTRmZWQ1NDg3MzQyMjA4ZTY0OGZhMTI4ZjFiYzI1OWQ1ZDI5NDczODc2ZWM0OTU2MjkyOWM3ODE4MWJjMGE1ZGIxMTNlODM3NTRmODVhNTEzNDQwMjU5YjVkNDU0N2M0YTgyZDNlMjI4ZTVmMjRkZjhhNTQ4NDQ5NGNlYzIxYjg1N2UxYWRmMmY2OWMiLCJpYXQiOjE3ODM4MDk2OTUsIm5iZiI6MTc4MzgwOTY5NSwiZXhwIjoxOTQxNTk0NDU1LCJzdWIiOjI5ODgwNTAsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.bMbTumHi1Jzjl49eZbNfY-S8X7zAYvpnPNOpLxv2RAm76ZcHJbtj_9QrCYL6Q679vtyA2SdB8vdhXmTtVRi4t7PO63Q1LDN4BQTxY5ZbxbBFrVdbkUi-9GC7QXuDcooxOuI8WC6CBqXr9pCyK3Hx-N8QCldTpmz54Hv9iyL0Y4t0ZLZ-F_-V_vWli9qTcMEODqsg-eC-dNgrqKVwdJjrQqWlMK60nNliYlTzxWJmYVjp0jmHHx6sQWRQNDy1Iu39sZefbFHqQKEJt77icupETH_-Y3h1cwSvv9aMh-kSndNrP-dYFSp6B3yWAXo6KhB19dK9HOHk-NGJNL4v4e13lQ"

with open("created_target_lisansarena_products.json", "r", encoding="utf-8") as f:
    products = json.load(f)

slug_map = {
    "Exxen Premium (1 Aylık Hesap)": "exxen",
    "Trendyol Yemek (150/100 İndirim)": "trendyol_yemek",
    "Trendyol Market (200/100 İndirim)": "trendyol_market",
    "Shell 100 TL Yakıt Puanı": "shell",
    "Steam Random Key (Gold)": "steam",
    "Office 365 Pro (1 Yıllık)": "office365"
}

cache_buster = int(time.time())

print("Deleting old products and re-creating with correct LISANSARENA covers...")
for idx, p in enumerate(products):
    product_id = p["id"]
    slug = slug_map.get(p["title"])
    if not slug:
        continue

    # Step 1: Delete old product
    del_url = f"https://api.shopier.com/v1/products/{product_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    req = urllib.request.Request(del_url, headers=headers, method="DELETE")
    print(f"[{idx+1}/6] Deleting old product: {p['title']} (ID: {product_id})...")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            print(f"  [DELETED] ID {product_id}")
    except urllib.error.HTTPError as e:
        print(f"  [DELETE FAILED] HTTP {e.code}: {e.reason}")
        try:
            print("  Body:", e.read().decode("utf-8"))
        except:
            pass
    except Exception as e:
        print(f"  [DELETE FAILED] {e}")
    time.sleep(1)

print("\nRe-creating products with updated LISANSARENA cover images...")
new_products = []
for idx, p in enumerate(products):
    slug = slug_map.get(p["title"])
    if not slug:
        continue

    image_url = f"https://froxy-bot.onrender.com/static/lisansarena_{slug}.png?v={cache_buster}"

    payload = {
        "title": p["title"],
        "description": p["description"],
        "type": "digital",
        "media": [
            {
                "type": "image",
                "url": image_url,
                "placement": 1
            }
        ],
        "priceData": {
            "currency": "TRY",
            "price": p["price"],
            "discount": False,
            "discountedPrice": p["price"],
            "shippingPrice": "0.00"
        },
        "stockQuantity": 999,
        "shippingPayer": "sellerPays"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    create_url = "https://api.shopier.com/v1/products"
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(create_url, data=req_data, headers=headers, method="POST")

    print(f"[{idx+1}/6] Creating: {p['title']} with image {image_url[:80]}...")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            res_body = r.read().decode("utf-8")
            res_data = json.loads(res_body)
            new_id = res_data.get("id")
            new_url = res_data.get("url")
            print(f"  [CREATED] New ID: {new_id} | URL: {new_url}")
            new_products.append({
                "id": new_id,
                "title": p["title"],
                "description": p["description"],
                "url": new_url,
                "imageUrl": image_url,
                "price": p["price"]
            })
    except urllib.error.HTTPError as e:
        print(f"  [CREATE FAILED] HTTP {e.code}: {e.reason}")
        try:
            print("  Body:", e.read().decode("utf-8"))
        except:
            pass
    except Exception as e:
        print(f"  [CREATE FAILED] {e}")
    time.sleep(1.5)

# Save new product list
with open("created_target_lisansarena_products.json", "w", encoding="utf-8") as f:
    json.dump(new_products, f, indent=2, ensure_ascii=False)
print(f"\nSaved {len(new_products)} new products to created_target_lisansarena_products.json")
print("Done!")
