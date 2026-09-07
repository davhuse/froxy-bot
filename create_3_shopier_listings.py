# -*- coding: utf-8 -*-
import urllib.request
import json
import ssl
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with open('restore_all_env.py', 'r', encoding='utf-8') as f:
    text = f.read()

token = re.search(r'"SHOPIER_KEYVADI_ACCESS_TOKEN":\s*"([^"]+)"', text).group(1)

NEW_PRODUCTS = [
    {
        "key": "yemeksepeti_200",
        "title": "Yemeksepeti 200₺'ye 200₺ İndirim Kodu",
        "price": 50.0,
        "desc": (
            "🍔 Yemeksepeti 200 TL ve Üzeri Sepetlerde 200 TL İndirim Kodu\n\n"
            "✨ Kampanya Detayları:\n"
            "• Yemeksepeti üzerinden vereceğiniz 200 TL ve üzeri tüm yemek siparişlerinizde anında 200 TL indirim sağlar.\n"
            "• Sepette kupon alanına girildiği anda indirim yansır.\n"
            "• Tüm geçerli restoranlarda kullanılabilir.\n\n"
            "📌 Teslimat & Destek:\n"
            "• Kod ödeme sonrası anında SMS ve ekranda teslim edilir.\n"
            "• Birebir telafi garantilidir."
        ),
        "image_url": "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp/assets/products/card_clean_yemeksepeti_200.jpg"
    },
    {
        "key": "coffy",
        "title": "Coffy 2 Kahve Alana 1'i Bedava Kupon Kodu",
        "price": 45.0,
        "desc": (
            "☕ Coffy 2 Kahve Alana 1'i Hediye Kupon Kodu\n\n"
            "✨ Kupon Detayları:\n"
            "• Tüm Coffy şubelerinde ve Coffy mobil uygulamasında geçerlidir.\n"
            "• 2 kahve siparişinizde 1 kahve anında bedava / hediye olur.\n"
            "• Sıcak ve soğuk kahve çeşitlerinde geçerlidir.\n\n"
            "📌 Teslimat:\n"
            "• Kupon kodu ödeme sonrası anında SMS ve sipariş ekranında teslim edilir."
        ),
        "image_url": "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp/assets/products/card_clean_coffy.jpg"
    },
    {
        "key": "migros",
        "title": "Migros 100 TL Alışveriş Bakiye Kodu",
        "price": 50.0,
        "desc": (
            "🛒 Migros 100 TL Alışveriş & Bakiye Çeki / Kodu\n\n"
            "✨ Detaylar:\n"
            "• Tüm Migros, 5M Migros, Migros Jet mağazalarında ve Migros Sanal Market uygulamasında geçerlidir.\n"
            "• Kasada veya uygulamada anında 100 TL indirim / bakiye olarak kullanılır.\n"
            "• Gıda, temizlik ve tüm market alışverişlerinde geçerlidir.\n\n"
            "📌 Teslimat:\n"
            "• Bakiye kodu satın alım sonrası anında iletilir."
        ),
        "image_url": "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp/assets/products/card_clean_migros.jpg"
    }
]

created_listings = []

for p in NEW_PRODUCTS:
    print(f"\nCreating Shopier listing for: {p['title']} ({p['price']} TL)...")
    payload = {
        "title": p["title"],
        "type": "digital",
        "description": p["desc"],
        "priceData": {
            "currency": "TRY",
            "price": p["price"],
            "discount": False,
            "shippingPrice": 0.0
        },
        "stockQuantity": 999,
        "shippingPayer": "sellerPays",
        "media": [
            {
                "type": "image",
                "url": p["image_url"],
                "placement": 1
            }
        ]
    }
    req = urllib.request.Request("https://api.shopier.com/v1/products", data=json.dumps(payload).encode('utf-8'), headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }, method="POST")

    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            data = json.loads(r.read().decode('utf-8'))
            prod_id = str(data.get("id"))
            url = data.get("url") or f"https://www.shopier.com/keyvadi/{prod_id}"
            print(f"   ✅ SUCCESS! ID: {prod_id} | URL: {url}")
            created_listings.append({
                "id": prod_id,
                "key": p["key"],
                "title": p["title"],
                "price": f"{p['price']:.2f} TL",
                "url": url,
                "image": p["image_url"]
            })
    except urllib.error.HTTPError as e:
        print(f"   ❌ HTTP Error {e.code}: {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print(f"\nTotal created listings: {len(created_listings)}")
with open('created_3_new_products.json', 'w', encoding='utf-8') as f:
    json.dump(created_listings, f, ensure_ascii=False, indent=2)

if created_listings:
    with open('keyvadi_shopier_links.json', 'r', encoding='utf-8') as f:
        existing = json.load(f)

    # Prepend new listings
    for item in reversed(created_listings):
        existing.insert(0, {
            "id": item["id"],
            "title": item["title"],
            "price": item["price"],
            "url": item["url"]
        })

    with open('keyvadi_shopier_links.json', 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"Updated keyvadi_shopier_links.json! Total items now: {len(existing)}")
