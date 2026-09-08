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
        "key": "tiktak",
        "title": "TikTak 1.000 TL Araç Kiralama İndirim Kodu",
        "price": 30.0,
        "badge": "🚗 1.000 TL Puan",
        "category": "tools",
        "category_label": "KUPON & İNDİRİM",
        "desc": (
            "🚗 TikTak 1.000 TL Araç Kiralama Puanı / İndirim Kodu\n\n"
            "✨ Kampanya & Kullanım Detayları:\n"
            "• TikTak ile yapacağınız ilk kiralamada 1.000 TL indirim sağlar.\n"
            "• Dakikalık, anında ve rezervasyonlu günlük kiralamalarda geçerlidir.\n"
            "• Araç kiralama ekranında 'Kupon Kodu Ekle' alanına girildiğinde tutardan anında 1.000 TL düşer.\n"
            "• Kampanya kodu tek kullanımlıktır.\n\n"
            "🔗 Kullanım Linki / Üye Olmak İçin:\n"
            "https://zhde.adj.st?adj_t=1lk2lthw\n\n"
            "📌 Teslimat & Garanti:\n"
            "• Kupon kodunuz ödeme sonrası anında ekranda ve SMS ile iletilir.\n"
            "• 7/24 Destek: @KeyvadiDestek"
        ),
        "image_url": "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp/assets/products/card_clean_tiktak.jpg",
        "local_image": "assets/products/card_clean_tiktak.jpg",
        "stock": ["KZNQKZIM"]
    },
    {
        "key": "flo",
        "title": "FLO 3.000 TL'ye 800 TL İndirim Çeki",
        "price": 20.0,
        "badge": "👟 800 TL İndirim",
        "category": "tools",
        "category_label": "KUPON & GİYİM",
        "desc": (
            "👟 FLO 3.000 TL ve Üzeri Alışverişlerde 800 TL İndirim Çeki\n\n"
            "✨ Kampanya & Kullanım Detayları:\n"
            "• FLO web sitesi ve mobil uygulamasında geçerlidir.\n"
            "• 3.000 TL ve üzeri sepetlerde anında 800 TL indirim sağlar.\n"
            "• Belirtilen kampanya linki içerisindeki ürünlerde geçerlidir.\n"
            "• Kod tek kullanımlıktır.\n\n"
            "🔗 Kampanya & Kullanım Linki:\n"
            "https://www.flo.com.tr/kampanya/ozel-indirim\n\n"
            "📌 Teslimat & Garanti:\n"
            "• Kod ödeme anında otomatik olarak teslim edilir.\n"
            "• 7/24 Destek: @KeyvadiDestek"
        ),
        "image_url": "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp/assets/products/card_clean_flo.jpg",
        "local_image": "assets/products/card_clean_flo.jpg",
        "stock": ["MY4ST7Z", "LN5SCNN"]
    },
    {
        "key": "lumberjack",
        "title": "Lumberjack 3.000 TL'ye 800 TL İndirim Çeki",
        "price": 20.0,
        "badge": "🥾 800 TL İndirim",
        "category": "tools",
        "category_label": "KUPON & MODA",
        "desc": (
            "🥾 Lumberjack 3.000 TL ve Üzeri Alışverişlerde 800 TL İndirim Çeki\n\n"
            "✨ Kampanya & Kullanım Detayları:\n"
            "• Kupon kodu Lumberjack web sitesine özeldir.\n"
            "• 3.000 TL ve üzerine 800 TL anında indirim sağlar.\n"
            "• Kampanya avantajlı ürünler linkinde geçerlidir.\n"
            "• Sepette kupon kodu alanına girildiğinde anında uygulanır. Tek kullanımlıktır.\n\n"
            "🔗 Kampanya & Kullanım Linki:\n"
            "https://www.lumberjack.com.tr/kampanya/lumberjack-avantajli-urunler\n\n"
            "📌 Teslimat & Garanti:\n"
            "• Kupon kodu ödeme sonrası anında teslim edilir.\n"
            "• 7/24 Destek: @KeyvadiDestek"
        ),
        "image_url": "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp/assets/products/card_clean_lumberjack.jpg",
        "local_image": "assets/products/card_clean_lumberjack.jpg",
        "stock": ["4SBF57Z", "77633FV"]
    },
    {
        "key": "instreet",
        "title": "In Street 4.500 TL'ye 1.250 TL İndirim Çeki",
        "price": 20.0,
        "badge": "🔥 1.250 TL İndirim",
        "category": "tools",
        "category_label": "KUPON & SNEAKER",
        "desc": (
            "👟 In Street 4.500 TL ve Üzeri Alışverişlerde 1.250 TL İndirim Çeki\n\n"
            "✨ Kampanya & Kullanım Detayları:\n"
            "• In Street mobil uygulaması ve web sitesinde geçerlidir.\n"
            "• 4.500 TL ve üzeri alışverişlerde sepette anında 1.250 TL indirim sağlar.\n"
            "• Belirtilen kampanya linki içerisindeki seçili ürünlerde geçerlidir.\n"
            "• Tek kullanımlıktır.\n\n"
            "🔗 Kampanya & Kullanım Linki:\n"
            "https://www.instreet.com.tr/kampanya/flash-kampanya-4\n\n"
            "📌 Teslimat & Garanti:\n"
            "• Kupon kodu ödeme sonrası anında teslim edilir.\n"
            "• 7/24 Destek: @KeyvadiDestek"
        ),
        "image_url": "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp/assets/products/card_clean_instreet.jpg",
        "local_image": "assets/products/card_clean_instreet.jpg",
        "stock": ["RNLCLX6"]
    },
    {
        "key": "enuygun",
        "title": "Enuygun Otobüs Biletinde 200 TL'ye Varan İndirim Kuponu",
        "price": 20.0,
        "badge": "🚌 200 TL Kupon",
        "category": "tools",
        "category_label": "KUPON & SEYAHAT",
        "desc": (
            "🚌 ENUYGUN Otobüs Biletlerinde 200 TL'ye Varan İndirim Kuponu\n\n"
            "✨ Kampanya Detayları:\n"
            "• ENUYGUN mobil uygulaması üzerinden yapılacak otobüs biletlerinde geçerlidir.\n"
            "• Ödeme sayfasında 'İndirim Kodunu kullan' alanına yazılarak indirimden yararlanılır.\n\n"
            "🎫 İndirim Baremleri:\n"
            "• 500 TL'ye kadar biletlerde: 25 TL indirim\n"
            "• 500 - 1.000 TL arası: 40 TL indirim\n"
            "• 1.000 - 1.200 TL arası: 60 TL indirim\n"
            "• 1.200 - 1.500 TL arası: 100 TL indirim\n"
            "• 1.500 TL üzeri: 200 TL indirim\n\n"
            "📱 Kullanım Şekli:\n"
            "ENUYGUN.com mobil uygulamasını indirip üye girişi yaparak otobüs bileti alırken kupon alanına kodu giriniz.\n\n"
            "📌 Teslimat & Garanti:\n"
            "• Kod ödeme sonrası anında teslim edilir.\n"
            "• 7/24 Destek: @KeyvadiDestek"
        ),
        "image_url": "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp/assets/products/card_clean_enuygun.jpg",
        "local_image": "assets/products/card_clean_enuygun.jpg",
        "stock": ["ENEEWQ315", "ENANA956C"]
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
            url = data.get("url") or f"https://www.shopier.com/{prod_id}"
            print(f"   ✅ SUCCESS! ID: {prod_id} | URL: {url}")
            created_listings.append({
                "id": prod_id,
                "key": p["key"],
                "title": p["title"],
                "price": f"{p['price']:.2f} TL",
                "price_num": p["price"],
                "url": url,
                "badge": p["badge"],
                "category": p["category"],
                "category_label": p["category_label"],
                "desc": p["desc"],
                "image": p["local_image"],
                "stock": p["stock"]
            })
    except urllib.error.HTTPError as e:
        print(f"   ❌ HTTP Error {e.code}: {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print(f"\nTotal created listings: {len(created_listings)}")
with open('newly_created_5_products.json', 'w', encoding='utf-8') as f:
    json.dump(created_listings, f, ensure_ascii=False, indent=2)

# 1. Update keyvadi_shopier_links.json
with open('keyvadi_shopier_links.json', 'r', encoding='utf-8') as f:
    existing_links = json.load(f)

for item in reversed(created_listings):
    existing_links.insert(0, {
        "id": item["id"],
        "title": item["title"],
        "price": item["price"],
        "url": item["url"]
    })

with open('keyvadi_shopier_links.json', 'w', encoding='utf-8') as f:
    json.dump(existing_links, f, ensure_ascii=False, indent=2)
print("Updated keyvadi_shopier_links.json!")

# 2. Update miniapp/products_db.json
with open('miniapp/products_db.json', 'r', encoding='utf-8') as f:
    products_db = json.load(f)

for item in reversed(created_listings):
    products_db.insert(0, {
        "id": item["id"],
        "title": item["title"],
        "price": f"{int(item['price_num']) if item['price_num'].is_integer() else item['price_num']:.2f}".replace('.', ',') + " TL",
        "price_num": item["price_num"],
        "category": item["category"],
        "image": item["image"],
        "badge": item["badge"],
        "url": item["url"],
        "description": item["desc"],
        "showcase": True,
        "is_vitrin": True,
        "category_label": item["category_label"],
        "delivery_type": "instant",
        "delivery_label": "Anında Kod Teslimatı",
        "max_qty": 5
    })

with open('miniapp/products_db.json', 'w', encoding='utf-8') as f:
    json.dump(products_db, f, ensure_ascii=False, indent=2)
print("Updated miniapp/products_db.json!")

# 3. Update licenses.json stock
with open('licenses.json', 'r', encoding='utf-8') as f:
    licenses_stock = json.load(f)

for item in created_listings:
    k = item["key"]
    existing_codes = licenses_stock.get(k, [])
    for code in item["stock"]:
        if code not in existing_codes:
            existing_codes.append(code)
    licenses_stock[k] = existing_codes

with open('licenses.json', 'w', encoding='utf-8') as f:
    json.dump(licenses_stock, f, ensure_ascii=False, indent=2)
print("Updated licenses.json with initial coupon stock codes!")

