import urllib.request
import urllib.error
import json
import ssl
import time
import subprocess
from datetime import datetime

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Correct working token from deploy_and_create_all.py
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5YjI5OWVmNzFlNTYyNDIzNDIxYTk5NDc1YzA2YWVlNiIsImp0aSI6IjkyMjYyZGFlMjliZmFkY2NhYTA1OTRmZWQ1NDg3MzQyMjA4ZTY0OGZhMTI4ZjFiYzI1OWQ1ZDI5NDczODc2ZWM0OTU2MjkyOWM3ODE4MWJjMGE1ZGIxMTNlODM3NTRmODVhNTEzNDQwMjU5YjVkNDU0N2M0YTgyZDNlMjI4ZTVmMjRkZjhhNTQ4NDQ5NGNlYzIxYjg1N2UxYWRmMmY2OWMiLCJpYXQiOjE3ODM4MDk2OTUsIm5iZiI6MTc4MzgwOTY5NSwiZXhwIjoxOTQxNTk0NDU1LCJzdWIiOjI5ODgwNTAsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.bMbTumHi1Jzjl49eZbNfY-S8X7zAYvpnPNOpLxv2RAm76ZcHJbtj_9QrCYL6Q679vtyA2SdB8vdhXmTtVRi4t7PO63Q1LDN4BQTxY5ZbxbBFrVdbkUi-9GC7QXuDcooxOuI8WC6CBqXr9pCyK3Hx-N8QCldTpmz54Hv9iyL0Y4t0ZLZ-F_-V_vWli9qTcMEODqsg-eC-dNgrqKVwdJjrQqWlMK60nNliYlTzxWJmYVjp0jmHHx6sQWRQNDy1Iu39sZefbFHqQKEJt77icupETH_-Y3h1cwSvv9aMh-kSndNrP-dYFSp6B3yWAXo6KhB19dK9HOHk-NGJNL4v4e13lQ"

missing_products = [
    {
        "title": "Exxen Reklamsız (3 Aylık)",
        "price": 36.99,
        "slug": "exxen",
        "desc": "Exxen Reklamsız 3 Aylık Üyelik. Giriş bilgileri sipariş sonrasında teslim edilir."
    },
    {
        "title": "Trendyol Go Yemek İndirim Kuponu (700 TL'ye 250 TL)",
        "price": 52.49,
        "slug": "trendyol_yemek",
        "desc": "Trendyol Go Yemek siparişinde 700 TL'ye 250 TL Net indirim sağlayan tek kullanımlık kupon."
    },
    {
        "title": "Trendyol Go Market İndirim Kuponu (900 TL'ye 250 TL)",
        "price": 52.49,
        "slug": "trendyol_market",
        "desc": "Trendyol Go Market siparişinde 900 TL'ye 250 TL Net indirim sağlayan tek kullanımlık kupon."
    },
    {
        "title": "Shell 75 TL Akaryakıt Puanı",
        "price": 15.90,
        "slug": "shell",
        "desc": "Shell istasyonlarında geçerli 75 TL değerinde akaryakıt puanı."
    }
]

created = []
cache_buster = int(time.time())

print("--- Creating missing products ---")
for idx, p in enumerate(missing_products):
    payload = {
        "title": p["title"],
        "description": p["desc"],
        "type": "digital",
        "media": [{"type": "image", "url": f"https://froxy-bot.onrender.com/static/la_{p['slug']}.png?v={cache_buster}", "placement": 1}],
        "priceData": {"currency": "TRY", "price": f"{p['price']:.2f}", "discount": False, "discountedPrice": f"{p['price']:.2f}", "shippingPrice": "0.00"},
        "stockQuantity": 999,
        "shippingPayer": "sellerPays"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    req = urllib.request.Request("https://api.shopier.com/v1/products", data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    print(f"[{idx+1}/{len(missing_products)}] Creating: {p['title']} ({p['price']:.2f} TL)...")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            res = json.loads(r.read().decode("utf-8"))
            print(f"  [OK] ID: {res.get('id')} | URL: {res.get('url')}")
            created.append({
                "id": res.get("id"),
                "title": p["title"],
                "description": p["desc"],
                "url": res.get("url"),
                "price": f"{p['price']:.2f}",
                "slug": p["slug"]
            })
    except urllib.error.HTTPError as e:
        print(f"  [FAIL] HTTP {e.code}")
        try:
            print("  ", e.read().decode("utf-8"))
        except:
            pass
    time.sleep(1.5)

# Integrate with catalog
if created:
    with open("lisansarena_shopier_links.json", "r", encoding="utf-8") as f:
        catalog = json.load(f)
        
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+0300")
    for cp in created:
        entry = {
            "id": cp["id"],
            "title": cp["title"],
            "description": cp["description"],
            "type": "digital",
            "dateCreated": now_str,
            "dateUpdated": now_str,
            "url": cp["url"],
            "media": [{"id": "1", "type": "image", "url": f"https://froxy-bot.onrender.com/static/la_{cp['slug']}.png", "placement": 1}],
            "priceData": {"currency": "TRY", "price": cp["price"], "discount": False, "discountedPrice": cp["price"], "shippingPrice": "0.00"},
            "stockStatus": "inStock",
            "stockQuantity": 999,
            "shippingPayer": "sellerPays",
            "categories": [], "variants": [], "options": [],
            "singleOption": False, "customListing": False, "customNote": "",
            "placementScore": "", "dispatchDuration": 0
        }
        catalog.append(entry)
        print(f"Catalog Added: {cp['title']}")
        
    with open("lisansarena_shopier_links.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=4, ensure_ascii=False)
        
    subprocess.run(["git", "add", "lisansarena_shopier_links.json"], cwd=r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam")
    subprocess.run(["git", "commit", "-m", "Add missing Exxen, Trendyol, and Shell products to LisansArena catalog"], cwd=r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam")
    subprocess.run(["git", "push", "old-origin", "main"], cwd=r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam")
    subprocess.run(["git", "push", "origin", "main"], cwd=r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam")
    print("Pushed to GitHub!")

print("All tasks completed.")
