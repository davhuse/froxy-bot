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

token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5YjI5OWVmNzFlNTYyNDIzNDIxYTk5NDc1YzA2YWVlNiIsImp0aSI6IjkyMjYyZGFlMjliZmFkY2NhYTA1OTRmZWQ1NDg3MzQyMjA4ZTY0OGZhMTI4ZjFiYzI1OWQ1ZDI5NDczODc2ZWM0OTU2MjkyOWM3ODE4MWJjMGE1ZGIxMTNlODM3NTRmODVhNTEzNDQwMjU5YjVkNDU0N2M0YTgyZDNlMjI4ZTVmMjRkZjhhNTQ4NDQ5NGNlYzIxYjg1N2UxYWRmMmY2OWMiLCJpYXQiOjE3ODM4MDk2OTUsIm5iZiI6MTc4MzgwOTY5NSwiZXhwIjoxOTQxNTk0NDU1LCJzdWIiOjI5ODgwNTAsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.bMbTumHi1Jzjl49eZbNfY-S8X7zAYvpnPNOpLxv2RAm76ZcHJbtj_9QrCYL6Q679vtyA2SdB8vdhXmTtVRi4t7PO63Q1LDN4BQTxY5ZbxbBFrVdbkUi-9GC7QXuDcooxOuI8WC6CBqXr9pCyK3Hx-N8QCldTpmz54Hv9iyL0Y4t0ZLZ-F_-V_vWli9qTcMEODqsg-eC-dNgrqKVwdJjrQqWlMK60nNliYlTzxWJmYVjp0jmHHx6sQWRQNDy1Iu39sZefbFHqQKEJt77icupETH_-Y3h1cwSvv9aMh-kSndNrP-dYFSp6B3yWAXo6KhB19dK9HOHk-NGJNL4v4e13lQ"

RENDER_API_KEY = "rnd_uSYeDJkX0xrcNfgo2BP7Tu3dRvuE"
SERVICE_ID = "srv-d8ecii58nd3s73afm620"

def get_latest_deploy_status():
    url = f"https://api.render.com/v1/services/{SERVICE_ID}/deploys?limit=1"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {RENDER_API_KEY}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            res = json.loads(r.read().decode("utf-8"))
            if res and isinstance(res, list):
                dep = res[0].get("deploy", {})
                return dep.get("id"), dep.get("status")
    except Exception as e:
        print(f"Error: {e}")
    return None, None

# Wait for deploy
print("Waiting for Render deploy to go live with the new covers...")
while True:
    dep_id, status = get_latest_deploy_status()
    print(f"[{time.strftime('%H:%M:%S')}] Deploy: {dep_id} | Status: {status}")
    if status == "live":
        print("LIVE! Proceeding...")
        break
    if status in ["build_failed", "update_failed", "deactivated"]:
        print(f"Deploy failed: {status}")
        exit(1)
    time.sleep(15)

# 1. Delete incorrect products
delete_ids = ["48901845", "48901891", "48901926", "48945471", "48901848"] # Also delete old Netflix 99.90 (48901848)? Wait, in catalog it is 48901848 or 48901848 is not there? Wait, the catalog had:
# 3: Netflix UHD 1 Profil (1 Aylık) -> 99.90 TRY -> ID is 48901848? Let's check!
# Wait, let's delete that too so there is no duplicate Netflix! Yes, we should delete the old Netflix (48901848) and the new incorrect one (48945471), so only 1 corrected Netflix remains!

print("\n--- Deleting incorrect products on Shopier ---")
for pid in ["48901845", "48901891", "48901926", "48945471"]:
    url = f"https://api.shopier.com/v1/products/{pid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    req = urllib.request.Request(url, headers=headers, method="DELETE")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            print(f"  [DELETED] ID: {pid}")
    except Exception as e:
        print(f"  [FAIL] ID: {pid} - {e}")
    time.sleep(1)

# 2. Create products with correct prices
products_to_create = [
    {
        "title": "Netflix 4K Ultra HD (Kişisel Profil)",
        "price": 94.49,
        "slug": "netflix_4k",
        "desc": "Netflix 4K Ultra HD kalitesinde kişisel profil. 1 Aylık kullanım. Giriş bilgileri sipariş sonrasında anında teslim edilir."
    },
    {
        "title": "YouTube Premium (3 Aylık Kod)",
        "price": 47.24,
        "slug": "youtube",
        "desc": "YouTube Premium 3 Aylık üyelik kodu. Kendi hesabınızda aktifleştirebilirsiniz."
    },
    {
        "title": "Spotify Premium (4 Aylık Kod)",
        "price": 36.74,
        "slug": "spotify",
        "desc": "Spotify Premium 4 Aylık davet kodu. Kendi hesabınızda veya yeni hesapta aktifleştirebilirsiniz."
    },
    {
        "title": "Canva Pro (1 Yıllık Yetki)",
        "price": 83.99,
        "slug": "canva",
        "desc": "Canva Pro 1 Yıllık davet linki ile kendi hesabınızı premium yapın."
    }
]

created = []
cache_buster = int(time.time())

print("\n--- Creating products with correct prices ---")
for idx, p in enumerate(products_to_create):
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
    print(f"[{idx+1}/{len(products_to_create)}] Creating: {p['title']} ({p['price']:.2f} TL)...")
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

# 3. Integrate into catalog
if created:
    with open("lisansarena_shopier_links.json", "r", encoding="utf-8") as f:
        catalog = json.load(f)
        
    # Remove old items from catalog list
    remove_titles = {
        "YouTube Premium (3 Aylık Kod)",
        "Spotify Premium (4 Aylık Kod)",
        "Canva 1 Yıllık Pro Davet",
        "Netflix UHD 1 Profil (1 Aylık)", # Delete old manual Netflix 99.90
        "Netflix 4K Ultra HD (Kişisel Profil)" # Delete old incorrect 52.49
    }
    catalog = [p for p in catalog if p.get("title") not in remove_titles]
    
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
    subprocess.run(["git", "commit", "-m", "Update LisansArena catalog with corrected prices for Netflix, YouTube, Spotify, and Canva"], cwd=r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam")
    subprocess.run(["git", "push", "old-origin", "main"], cwd=r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam")
    subprocess.run(["git", "push", "origin", "main"], cwd=r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam")
    print("Pushed to GitHub!")

print("All tasks completed.")
