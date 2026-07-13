import urllib.request
import urllib.error
import json
import ssl
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJiOGI0MjA0NWM1NDY2ZDdiMWQwODc0OGUzZTBkNDlmNSIsImp0aSI6Ijg1MGQwMzdmMDA2MWMyMjc4MDBkNDcxNzJmMmQ1NTMxZDQ4ODNhMjMzM2RkNTVmNmYwMDkwOGM5NmEyZjIwZDhkMzA5YmQ3YTQ5ZjM1MmViYjE1ZjdiZmMzNWIyODUxYzI0OTcxZjJjMzhkNGIzMGFlMzI3NDBlZGQzOTNhYmYzMWFkYmYyMWE4ZDAzNThlYWRiYTA3YWQwZjFjYTJlY2YiLCJpYXQiOjE3ODM5NjAzNTYsIm5iZiI6MTc4Mzk2MDM1NiwiZXhwIjoxOTQxNzQ1MTE2LCJzdWIiOjI1MDk0OTMsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.Qm7lPz2dY1-RpllpREC8mfruDPCTOnBufCz3pxSMmvEszdJlBvD0_eL_9h90DyiuTEXR6Q-Sbzt06H29tAeLGyCIRoMCgKluB69s_T6lLx5xpdV_M0KsppXIfsuxM3chcyVtYoT-qTXRFCNH3S_1jchf8CucsWdtdIfRAMINuy3IiBAAiBNPXWzsf2O2ChgPod7eIGoF5DNl2uVXWpgHJjMHb8fqw2F5CLl4Zl-7h5NiUDz5Qyhp2ZUZ2D7attYpklgOyk3mh9J7sEAyas6dqv5lMtH2lWT84BlLz5XuzM_CTKh436LEZIQWdwKp1zHjsAHJmHGmmWdwd0lylCcrwQ"

url = "https://api.shopier.com/v1/products"

missing_products = [
    {"name": "Eski Tarihli Telegram Hesabı (+1 No'lu)", "category": "Numbers", "price": 149.90, "slug": "telegram_account", "desc": "1 Ocak veya öncesi eski tarihli kurumlu onaylı Telegram hesabı (+1 numaralı)."},
    {"name": "Perplexity Pro (1 Aylık Hesap)", "category": "AI", "price": 119.90, "slug": "perplexity_pro", "desc": "Perplexity Pro Yapay Zeka Arama Motoru 1 Aylık Hesap. Giriş garantilidir."},
    {"name": "DeepL AI (1 Aylık) - Kişisel Hesap", "category": "AI", "price": 59.90, "slug": "deepl_kisisel", "desc": "DeepL Pro Çeviri 1 Aylık Kişisel Kullanım Hesabı. Giriş garantilidir."},
    {"name": "DeepL AI (1 Aylık) - Ortak Hesap", "category": "AI", "price": 29.90, "slug": "deepl_ortak", "desc": "DeepL Pro Çeviri 1 Aylık Ortak Kullanım Hesabı. Sınırsız döküman çevirme."},
    {"name": "Scribd (1 Aylık) - Kişisel Hesap", "category": "Design", "price": 59.90, "slug": "scribd_kisisel", "desc": "Scribd Premium 1 Aylık Kişisel Kullanım Hesabı. Giriş garantilidir."},
    {"name": "Scribd (1 Aylık) - Ortak Hesap", "category": "Design", "price": 29.90, "slug": "scribd_ortak", "desc": "Scribd Premium 1 Aylık Ortak Kullanım Hesabı. Sınırsız kitap, döküman ve sesli kitap okuma."},
    {"name": "Magnific AI Ortak (1 Aylık Business Hesap)", "category": "AI", "price": 49.90, "slug": "magnific_ai", "desc": "Magnific AI 1 Aylık Ortak Business Hesabı. Görsel büyütme ve yapay zeka ile netleştirme."},
    {"name": "Crunchyroll Özel Profil (1 Aylık)", "category": "Entertainment", "price": 59.90, "slug": "crunchyroll_ozel", "desc": "Crunchyroll Premium 1 Aylık Kişisel Profil. Kendi izleme listenizi oluşturabilirsiniz."},
    {"name": "Crunchyroll Ortak Hesap (1 Aylık)", "category": "Entertainment", "price": 39.90, "slug": "crunchyroll_ortak", "desc": "Crunchyroll Premium 1 Aylık Ortak Kullanım Hesabı. Giriş garantilidir."},
    {"name": "Grammarly Pro (1 Haftalık) - Kendi Hesabınıza", "category": "Design", "price": 79.90, "slug": "grammarly_haftalik", "desc": "Grammarly Pro 1 haftalık bireysel üyelik. Kendi kişisel hesabınıza tanımlanır."},
    {"name": "Grammarly Pro (1 Aylık) - Ortak Hesap", "category": "Design", "price": 49.90, "slug": "grammarly_ortak", "desc": "Grammarly Pro 1 Aylık Ortak Kullanım Hesabı. Hata analizi ve kelime geliştirme özellikleri açıktır."}
]

created_list = []

print("Starting Shopier Product Creation via REST API...")
for idx, p in enumerate(missing_products):
    payload = {
        "title": p["name"],
        "description": p["desc"],
        "type": "digital",
        "media": [
            {
                "type": "image",
                "url": f"https://froxy-bot.onrender.com/static/keyvadi_{p['slug']}.png",
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
    
    print(f"Creating product {idx+1}/{len(missing_products)}: {p['name']}...")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            res_body = r.read().decode("utf-8")
            res_data = json.loads(res_body)
            print(f"  [SUCCESS] Product ID: {res_data.get('id')} | URL: {res_data.get('url')}")
            
            created_list.append({
                "id": res_data.get("id"),
                "title": p["name"],
                "price": f"{p['price']:.2f} TL",
                "url": res_data.get("url"),
                "slug": p["slug"]
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
with open("created_shopier_products.json", "w", encoding="utf-8") as f:
    json.dump(created_list, f, indent=2, ensure_ascii=False)
print("Created products saved to created_shopier_products.json")
