import urllib.request
import urllib.error
import json
import ssl
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5YjI5OWVmNzFlNTYyNDIzNDIxYTk5NDc1YzA2YWVlNiIsImp0aSI6IjkyMjYyZGFlMjliZmFkY2NhYTA1OTRmZWQ1NDg3MzQyMjA4ZTY0OGZhMTI4ZjFiYzI1OWQ1ZDI5NDczODc2ZWM0OTU2MjkyOWM3ODE4MWJjMGE1ZGIxMTNlODM3NTRmODVhNTEzNDQwMjU5YjVkNDU0N2M0YTgyZDNlMjI4ZTVmMjRkZjhhNTQ4NDQ5NGNlYzIxYjg1N2UxYWRmMmY2OWMiLCJpYXQiOjE3ODM4MDk2OTUsIm5iZiI6MTc4MzgwOTY5NSwiZXhwIjoxOTQxNTk0NDU1LCJzdWIiOjI5ODgwNTAsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.bMbTumHi1Jzjl49eZbNfY-S8X7zAYvpnPNOpLxv2RAm76ZcHJbtj_9QrCYL6Q679vtyA2SdB8vdhXmTtVRi4t7PO63Q1LDN4BQTxY5ZbxbBFrVdbkUi-9GC7QXuDcooxOuI8WC6CBqXr9pCyK3Hx-N8QCldTpmz54Hv9iyL0Y4t0ZLZ-F_-V_vWli9qTcMEODqsg-eC-dNgrqKVwdJjrQqWlMK60nNliYlTzxWJmYVjp0jmHHx6sQWRQNDy1Iu39sZefbFHqQKEJt77icupETH_-Y3h1cwSvv9aMh-kSndNrP-dYFSp6B3yWAXo6KhB19dK9HOHk-NGJNL4v4e13lQ"

url = "https://api.shopier.com/v1/products"

target_products = [
    {"name": "Exxen Premium (1 Aylık Hesap)", "price": 34.99, "slug": "exxen", "desc": "Exxen Premium 1 Aylık Reklamsız Üyelik."},
    {"name": "Trendyol Yemek (150/100 İndirim)", "price": 19.99, "slug": "trendyol_yemek", "desc": "Trendyol Yemek 150 TL siparişe 100 TL indirim sağlayan özel tanımlı hesap."},
    {"name": "Trendyol Market (200/100 İndirim)", "price": 19.99, "slug": "trendyol_market", "desc": "Trendyol Market 200 TL siparişe 100 TL indirim sağlayan özel tanımlı hesap."},
    {"name": "Shell 100 TL Yakıt Puanı", "price": 49.99, "slug": "shell", "desc": "Shell ClubSmart kartınıza yüklenebilir 100 TL değerinde yakıt puanı."},
    {"name": "Steam Random Key (Gold)", "price": 9.99, "slug": "steam", "desc": "Steam platformunda geçerli, yüksek değerli oyun çıkma garantili Gold Random Key."},
    {"name": "Office 365 Pro (1 Yıllık)", "price": 39.99, "slug": "office365", "desc": "Microsoft Office 365 1 Yıllık Bireysel Premium Lisans."}
]

created_list = []

print("Starting target LisansArena Product Creation via REST API...")
for idx, p in enumerate(target_products):
    payload = {
        "title": p["name"],
        "description": p["desc"],
        "type": "digital",
        "media": [
            {
                "type": "image",
                "url": f"https://froxy-bot.onrender.com/static/lisansarena_{p['slug']}.png",
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
    
    print(f"Creating product {idx+1}/{len(target_products)}: {p['name']}...")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            res_body = r.read().decode("utf-8")
            res_data = json.loads(res_body)
            print(f"  [SUCCESS] Product ID: {res_data.get('id')} | URL: {res_data.get('url')}")
            
            created_list.append({
                "id": res_data.get("id"),
                "title": p["name"],
                "description": p["desc"],
                "url": res_data.get("url"),
                "imageUrl": f"https://cdn.shopier.app/pictures_large/lisansarena_{p['slug']}.jpg",
                "price": f"{p['price']:.2f}"
            })
    except urllib.error.HTTPError as e:
        print(f"  [FAILED] HTTP Error {e.code}: {e.reason}")
        try:
            print("  Body:", e.read().decode("utf-8"))
        except:
            pass
    except Exception as e:
        print(f"  [FAILED] Other error: {e}")
    time.sleep(1.5)

# Save created products locally
with open("created_target_lisansarena_products.json", "w", encoding="utf-8") as f:
    json.dump(created_list, f, indent=2, ensure_ascii=False)
print("Created target products saved to created_target_lisansarena_products.json")
