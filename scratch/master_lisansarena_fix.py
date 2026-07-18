import urllib.request
import urllib.error
import json
import ssl
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5YjI5OWVmNzFlNTYyNDIzNDIxYTk5NDc1YzA2YWVlNiIsImp0aSI6IjkyMjYyZGFlMjliZmFkY2NhYTA1OTRmZWQ1NDg3MzQyMjA4ZTY0OGZhMTI4ZjFiYzI1OWQ1ZDI5NDczODc2ZWM0OTU2MjkyOWM3ODE4MWJjMGE1ZGIxMTNlODM3NTRmODVhNTEzNDQwMjU5YjVkNDU0N2M0YTgyZDNlMjI4ZTVmMjRkZjhhNTQ4NDQ5NGNlYzIxYjg1N2UxYWRmMmY2OWMiLCJpYXQiOjE3ODM4MDk2OTUsIm5iZiI6MTc4MzgwOTY5NSwiZXhwIjoxOTQxNTk0NDU1LCJzdWIiOjI5ODgwNTAsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.bMbTumHi1Jzjl49eZbNfY-S8X7zAYvpnPNOpLxv2RAm76ZcHJbtj_9QrCYL6Q679vtyA2SdB8vdhXmTtVRi4t7PO63Q1LDN4BQTxY5ZbxbBFrVdbkUi-9GC7QXuDcooxOuI8WC6CBqXr9pCyK3Hx-N8QCldTpmz54Hv9iyL0Y4t0ZLZ-F_-V_vWli9qTcMEODqsg-eC-dNgrqKVwdJjrQqWlMK60nNliYlTzxWJmYVjp0jmHHx6sQWRQNDy1Iu39sZefbFHqQKEJt77icupETH_-Y3h1cwSvv9aMh-kSndNrP-dYFSp6B3yWAXo6KhB19dK9HOHk-NGJNL4v4e13lQ"

# ====== STEP 1: Delete 6 wrong products ======
delete_ids = ["48944992", "48944996", "48944997", "48944998", "48945001", "48945004"]
print("=" * 60)
print("STEP 1: Deleting 6 wrongly added products...")
print("=" * 60)
for pid in delete_ids:
    url = f"https://api.shopier.com/v1/products/{pid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    req = urllib.request.Request(url, headers=headers, method="DELETE")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            print(f"  [DELETED] ID {pid}")
    except urllib.error.HTTPError as e:
        print(f"  [FAILED] ID {pid} - HTTP {e.code}")
    time.sleep(1)

# ====== STEP 2: Update Gemini Pro titles to 12 Aylık ======
print("\n" + "=" * 60)
print("STEP 2: Updating Gemini Pro titles to 12 Aylık...")
print("=" * 60)
gemini_updates = [
    {"id": "48901861", "new_title": "Gemini Pro Davet (12 Aylık)"},
    {"id": "48901862", "new_title": "Gemini Pro Premium Hesap (12 Aylık)"},
]
for gu in gemini_updates:
    url = f"https://api.shopier.com/v1/products/{gu['id']}"
    payload = {"title": gu["new_title"]}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            print(f"  [UPDATED] {gu['id']} -> {gu['new_title']}")
    except urllib.error.HTTPError as e:
        print(f"  [FAILED] {gu['id']} - HTTP {e.code}: {e.reason}")
        try:
            print("  Body:", e.read().decode("utf-8"))
        except:
            pass
    time.sleep(1)

# ====== STEP 3: Create missing products (KeyVadi birebir, %5 artış) ======
print("\n" + "=" * 60)
print("STEP 3: Creating missing products with %5 price increase...")
print("=" * 60)

cache_buster = int(time.time())

new_products = [
    {"title": "Netflix 4K Ultra HD (Kişisel Profil)", "price": 52.49, "desc": "Netflix 4K Ultra HD kalitesinde kişisel profil. 1 Aylık kullanım."},
    {"title": "Microsoft Office 365 (1 Yıllık Hesap)", "price": 73.50, "desc": "Microsoft Office 365 1 Yıllık tam lisanslı hesap. Word, Excel, PowerPoint ve tüm Office uygulamaları dahil."},
    {"title": "Windows 10/11 Pro Lisans Anahtarı (Key)", "price": 73.50, "desc": "Windows 10/11 Pro orijinal lisans anahtarı. Ömür boyu geçerli aktivasyon kodu."},
    {"title": "Steam İstediğiniz Oyun (Ortak Hesap)", "price": 63.00, "desc": "Steam'de istediğiniz oyunu ortak hesap üzerinden oynayabilirsiniz. Hesap bilgileri teslim edilir."},
    {"title": "Super Grok (1 Aylık Hesap)", "price": 472.49, "desc": "xAI Super Grok 1 Aylık premium hesap. Sınırsız Grok-3 erişimi."},
    {"title": "Super Grok (3 Aylık Hesap)", "price": 997.49, "desc": "xAI Super Grok 3 Aylık premium hesap. Sınırsız Grok-3 erişimi."},
    {"title": "Super Grok (6 Aylık Hesap)", "price": 1574.99, "desc": "xAI Super Grok 6 Aylık premium hesap. Sınırsız Grok-3 erişimi."},
    {"title": "Super Grok (12 Aylık Hesap)", "price": 2414.99, "desc": "xAI Super Grok 12 Aylık premium hesap. Sınırsız Grok-3 erişimi."},
    {"title": "Gamma Ultra (1 Aylık Hesap)", "price": 472.49, "desc": "Gamma AI Ultra 1 Aylık hesap. Sınırsız sunum ve doküman oluşturma."},
    {"title": "Gamma Pro (1 Aylık Hesap)", "price": 314.99, "desc": "Gamma AI Pro 1 Aylık hesap. Gelişmiş sunum ve doküman oluşturma özellikleri."},
    {"title": "Gemini Ultra (Davet Linki)", "price": 419.99, "desc": "Google Gemini Ultra davet linki. Kendi hesabınıza tanımlanır."},
    {"title": "Gemini Ultra (2.5k Kredili Hesap)", "price": 629.99, "desc": "Google Gemini Ultra 2500 kredi yüklü premium hesap."},
]

created_products = []
for idx, p in enumerate(new_products):
    payload = {
        "title": p["title"],
        "description": p["desc"],
        "type": "digital",
        "media": [
            {
                "type": "image",
                "url": f"https://froxy-bot.onrender.com/static/lisansarena_placeholder.png?v={cache_buster}",
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
    req = urllib.request.Request("https://api.shopier.com/v1/products", data=req_data, headers=headers, method="POST")
    
    print(f"[{idx+1}/{len(new_products)}] Creating: {p['title']} ({p['price']:.2f} TL)...")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            res = json.loads(r.read().decode("utf-8"))
            new_id = res.get("id")
            new_url = res.get("url")
            print(f"  [CREATED] ID: {new_id} | URL: {new_url}")
            created_products.append({
                "id": new_id,
                "title": p["title"],
                "description": p["desc"],
                "url": new_url,
                "price": f"{p['price']:.2f}"
            })
    except urllib.error.HTTPError as e:
        print(f"  [FAILED] HTTP {e.code}: {e.reason}")
        try:
            print("  Body:", e.read().decode("utf-8"))
        except:
            pass
    time.sleep(1.5)

with open("created_final_lisansarena_products.json", "w", encoding="utf-8") as f:
    json.dump(created_products, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(created_products)} new products.")
print("All steps completed!")
