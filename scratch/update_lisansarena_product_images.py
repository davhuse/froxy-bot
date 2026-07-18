import urllib.request
import urllib.error
import json
import ssl
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5YjI5OWVmNzFlNTYyNDIzNDIxYTk5NDc1YzA2YWVlNiIsImp0aSI6IjkyMjYyZGFlMjliZmFkY2NhYTA1OTRmZWQ1NDg3MzQyMjA4ZTY0OGZhMTI4ZjFiYzI1OWQ1ZDI5NDczODc2ZWM0OTU2MjkyOWM3ODE4MWJjMGE1ZGIxMTNlODM3NTRmODVhYjVkNDU0N2M0YTgyZDNlMjI4ZTVmMjRkZjhhNTQ4NDQ5NGNlYzIxYjg1N2UxYWRmMmY2OWMiLCJpYXQiOjE3ODM4MDk2OTUsIm5iZiI6MTc4MzgwOTY5NSwiZXhwIjoxOTQxNTk0NDU1LCJzdWIiOjI5ODgwNTAsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.bMbTumHi1Jzjl49eZbNfY-S8X7zAYvpnPNOpLxv2RAm76ZcHJbtj_9QrCYL6Q679vtyA2SdB8vdhXmTtVRi4t7PO63Q1LDN4BQTxY5ZbxbBFrVdbkUi-9GC7QXuDcooxOuI8WC6CBqXr9pCyK3Hx-N8QCldTpmz54Hv9iyL0Y4t0ZLZ-F_-V_vWli9qTcMEODqsg-eC-dNgrqKVwdJjrQqWlMK60nNliYlTzxWJmYVjp0jmHHx6sQWRQNDy1Iu39sZefbFHqQKEJt77icupETH_-Y3h1cwSvv9aMh-kSndNrP-dYFSp6B3yWAXo6KhB19dK9HOHk-NGJNL4v4e13lQ"

with open("created_target_lisansarena_products.json", "r", encoding="utf-8") as f:
    products = json.load(f)

# Slugs mapping for images
slug_map = {
    "Exxen Premium (1 Aylık Hesap)": "exxen",
    "Trendyol Yemek (150/100 İndirim)": "trendyol_yemek",
    "Trendyol Market (200/100 İndirim)": "trendyol_market",
    "Shell 100 TL Yakıt Puanı": "shell",
    "Steam Random Key (Gold)": "steam",
    "Office 365 Pro (1 Yıllık)": "office365"
}

print("Starting Shopier Product Update to force cover image refresh...")
for idx, p in enumerate(products):
    product_id = p["id"]
    slug = slug_map.get(p["title"])
    if not slug:
        print(f"Warning: Slug not found for {p['title']}")
        continue
        
    url = f"https://api.shopier.com/v1/products/{product_id}"
    
    # We update the product with the same details but new image URL to trigger redownload
    payload = {
        "title": p["title"],
        "description": p["description"],
        "media": [
            {
                "type": "image",
                "url": f"https://froxy-bot.onrender.com/static/lisansarena_{slug}.png",
                "placement": 1
            }
        ],
        "priceData": {
            "currency": "TRY",
            "price": p["price"],
            "discount": False,
            "discountedPrice": p["price"]
        }
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=headers, method="PUT")
    
    print(f"Updating product {idx+1}/{len(products)}: {p['title']}...")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            print(f"  [SUCCESS] Updated ID {product_id}")
    except urllib.error.HTTPError as e:
        print(f"  [FAILED] HTTP Error {e.code}: {e.reason}")
        try:
            print("  Body:", e.read().decode("utf-8"))
        except:
            pass
    except Exception as e:
        print(f"  [FAILED] Other error: {e}")
    time.sleep(1.5)

print("Product image updates completed.")
