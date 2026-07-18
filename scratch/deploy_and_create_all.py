import urllib.request
import urllib.error
import json
import ssl
import time

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
print("Waiting for Render deploy to go live...")
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

# Delete old Gemini Pro products (can't update, 403)
print("\n--- Deleting old Gemini Pro products ---")
for pid in ["48901861", "48901862"]:
    url = f"https://api.shopier.com/v1/products/{pid}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Authorization": f"Bearer {token}", "Accept": "application/json"}
    req = urllib.request.Request(url, headers=headers, method="DELETE")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            print(f"  [DELETED] {pid}")
    except urllib.error.HTTPError as e:
        print(f"  [FAILED] {pid} - HTTP {e.code}")
    time.sleep(1)

# Create all products
products = [
    {"title": "Netflix 4K Ultra HD (Kişisel Profil)", "price": 52.49, "slug": "netflix_4k", "desc": "Netflix 4K Ultra HD kalitesinde kişisel profil. 1 Aylık kullanım."},
    {"title": "Microsoft Office 365 (1 Yıllık Hesap)", "price": 73.50, "slug": "office365", "desc": "Microsoft Office 365 1 Yıllık tam lisanslı hesap. Word, Excel, PowerPoint ve tüm Office uygulamaları dahil."},
    {"title": "Windows 10/11 Pro Lisans Anahtarı (Key)", "price": 73.50, "slug": "windows_pro", "desc": "Windows 10/11 Pro orijinal lisans anahtarı. Ömür boyu geçerli aktivasyon kodu."},
    {"title": "Steam İstediğiniz Oyun (Ortak Hesap)", "price": 63.00, "slug": "steam_oyun", "desc": "Steam'de istediğiniz oyunu ortak hesap üzerinden oynayabilirsiniz. Hesap bilgileri teslim edilir."},
    {"title": "Super Grok (1 Aylık Hesap)", "price": 472.49, "slug": "super_grok_1m", "desc": "xAI Super Grok 1 Aylık premium hesap. Sınırsız Grok-3 erişimi."},
    {"title": "Super Grok (3 Aylık Hesap)", "price": 997.49, "slug": "super_grok_3m", "desc": "xAI Super Grok 3 Aylık premium hesap. Sınırsız Grok-3 erişimi."},
    {"title": "Super Grok (6 Aylık Hesap)", "price": 1574.99, "slug": "super_grok_6m", "desc": "xAI Super Grok 6 Aylık premium hesap. Sınırsız Grok-3 erişimi."},
    {"title": "Super Grok (12 Aylık Hesap)", "price": 2414.99, "slug": "super_grok_12m", "desc": "xAI Super Grok 12 Aylık premium hesap. Sınırsız Grok-3 erişimi."},
    {"title": "Gamma Ultra (1 Aylık Hesap)", "price": 472.49, "slug": "gamma_ultra", "desc": "Gamma AI Ultra 1 Aylık hesap. Sınırsız sunum ve doküman oluşturma."},
    {"title": "Gamma Pro (1 Aylık Hesap)", "price": 314.99, "slug": "gamma_pro", "desc": "Gamma AI Pro 1 Aylık hesap. Gelişmiş sunum ve doküman oluşturma özellikleri."},
    {"title": "Gemini Ultra (Davet Linki)", "price": 419.99, "slug": "gemini_ultra_davet", "desc": "Google Gemini Ultra davet linki. Kendi hesabınıza tanımlanır."},
    {"title": "Gemini Ultra (2.5k Kredili Hesap)", "price": 629.99, "slug": "gemini_ultra_2500", "desc": "Google Gemini Ultra 2500 kredi yüklü premium hesap."},
    {"title": "Gemini Pro Davet (12 Aylık)", "price": 131.24, "slug": "gemini_pro_davet_12m", "desc": "Google Gemini Pro 12 Aylık davet linki. Kendi hesabınıza tanımlanır."},
    {"title": "Gemini Pro Premium Hesap (12 Aylık)", "price": 209.89, "slug": "gemini_pro_hesap_12m", "desc": "Google Gemini Pro 12 Aylık premium hesap."},
]

print(f"\n--- Creating {len(products)} products ---")
created = []
for idx, p in enumerate(products):
    payload = {
        "title": p["title"],
        "description": p["desc"],
        "type": "digital",
        "media": [{"type": "image", "url": f"https://froxy-bot.onrender.com/static/la_{p['slug']}.png", "placement": 1}],
        "priceData": {"currency": "TRY", "price": f"{p['price']:.2f}", "discount": False, "discountedPrice": f"{p['price']:.2f}", "shippingPrice": "0.00"},
        "stockQuantity": 999,
        "shippingPayer": "sellerPays"
    }
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}
    req = urllib.request.Request("https://api.shopier.com/v1/products", data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    print(f"[{idx+1}/{len(products)}] {p['title']} ({p['price']:.2f} TL)...")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            res = json.loads(r.read().decode("utf-8"))
            print(f"  [OK] ID: {res.get('id')} | URL: {res.get('url')}")
            created.append({"id": res.get("id"), "title": p["title"], "description": p["desc"], "url": res.get("url"), "price": f"{p['price']:.2f}"})
    except urllib.error.HTTPError as e:
        print(f"  [FAIL] HTTP {e.code}")
        try: print("  ", e.read().decode("utf-8"))
        except: pass
    time.sleep(1.5)

with open("created_final_lisansarena_products.json", "w", encoding="utf-8") as f:
    json.dump(created, f, indent=2, ensure_ascii=False)
print(f"\nDone! Created {len(created)}/{len(products)} products.")
