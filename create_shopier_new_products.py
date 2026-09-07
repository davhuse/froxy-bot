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
        "key": "ssport",
        "title": "S Sport Plus (1 Aylık)",
        "price": 70.0,
        "desc": (
            "⚽ S Sport Plus 1 Aylık Premium Paket\n\n"
            "✨ Özellikler:\n"
            "• Premier League, La Liga, Serie A, EuroLeague, NBA, F1 ve tüm spor yayınları.\n"
            "• Canlı maçlar ve geçmiş karşılaşmaları tekrar izleme imkanı.\n"
            "• Full HD yüksek yayın kalitesi ve çoklu cihaz desteği.\n\n"
            "📌 Teslimat & Garanti:\n"
            "• Sipariş sonrası bilgiler anında iletilir.\n"
            "• 1 ay boyunca %100 değişim ve telafi garantisi."
        ),
        "image_url": "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp/assets/products/card_clean_ssport.jpg"
    },
    {
        "key": "yemeksepeti",
        "title": "Yemeksepeti 450₺'ye 350₺ İndirim Kodu",
        "price": 60.0,
        "desc": (
            "🍔 Yemeksepeti 450 TL Sepete 350 TL İndirim Kuponu\n\n"
            "✨ Kampanya Detayları:\n"
            "• Yemeksepeti üzerinden vereceğiniz 450 TL ve üzeri yemek siparişlerinde 350 TL indirim sağlar.\n"
            "• Sepetinizde kupon alanına girildiğinde anında düşer.\n"
            "• Tüm geçerli restoranlarda geçerlidir.\n\n"
            "📌 Teslimat:\n"
            "• Kupon kodu ödeme sonrası anında teslim edilir."
        ),
        "image_url": "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp/assets/products/card_clean_yemeksepeti.jpg"
    },
    {
        "key": "turna",
        "title": "Turna.com 600 TL Uçak Bileti İndirim Kuponu",
        "price": 70.0,
        "desc": (
            "✈️ Turna.com Uçak Biletlerinde 600 TL İndirim Kodu\n\n"
            "✨ Kupon Detayları:\n"
            "• Turna.com web sitesi veya mobil uygulaması üzerinden satın alınacak tek yön veya gidiş-dönüş uçak biletlerinde 600 TL indirim sağlar.\n"
            "• Yurt içi ve yurt dışı her yöne uçuşlarda geçerlidir.\n"
            "• Vodafone Red / Vodafone Pay ek nakit iade kampanyalarıyla birleştirilebilir.\n\n"
            "📌 Teslimat:\n"
            "• Kod satın alım anında SMS ve sipariş ekranında gösterilir."
        ),
        "image_url": "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp/assets/products/card_clean_turna.jpg"
    },
    {
        "key": "tiklagelsin",
        "title": "Tıkla Gelsin® 400₺'ye 200₺ Yemek Kupon Kodu",
        "price": 50.0,
        "desc": (
            "🍟 Tıkla Gelsin® 400 TL ve Üzerine 200 TL İndirim Kodu\n\n"
            "✨ Detaylar:\n"
            "• Burger King, Popeyes, Arby's, Usta Dönerci, Sbarro siparişlerinde geçerli.\n"
            "• Tıkla Gelsin® Gel Al ve Sana Gelsin kanallarındaki 400 TL ve üzeri yemek siparişlerinde 200 TL indirim kazandırır.\n"
            "• Sepette kupon alanına girildiği anda indirim yansır.\n\n"
            "📌 Teslimat:\n"
            "• Kupon kodu satın alım sonrası anında iletilir."
        ),
        "image_url": "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp/assets/products/card_clean_tiklagelsin.jpg"
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
                "url": url
            })
    except urllib.error.HTTPError as e:
        print(f"   ❌ HTTP Error {e.code}: {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print(f"\nTotal created listings: {len(created_listings)}")
with open('newly_created_shopier_products.json', 'w', encoding='utf-8') as f:
    json.dump(created_listings, f, ensure_ascii=False, indent=2)

# Update keyvadi_shopier_links.json
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
