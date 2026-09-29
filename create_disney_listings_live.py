# -*- coding: utf-8 -*-
import json
import urllib.request
import ssl
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('temp_shopier_tokens.json', 'r', encoding='utf-8') as f:
    tokens = json.load(f)

ctx = ssl._create_unverified_context()

PRODUCTS_TO_CREATE = [
    {
        "brand": "keyvadi",
        "key": "kv_disney_ortak",
        "title": "Disney+ 1 Aylık Ortak Hesap",
        "price": 49.90,
        "desc": "Disney+ 1 Aylık Ortak Hesap. 4K Ultra HD kalitesinde kesintisiz erişim. 30 gün boyunca telafi ve destek garantilidir. Otomatik teslimat.",
        "img_url": "https://bot-service-production-9d74.up.railway.app/static/disney_ortak_49.jpg",
        "local_img": "assets/products/disney_ortak_49.jpg",
        "category": "streaming",
        "category_label": "DİZİ & FİLM"
    },
    {
        "brand": "keyvadi",
        "key": "kv_disney_ozel",
        "title": "Disney+ 1 Aylık Özel Profil",
        "price": 99.90,
        "desc": "Disney+ 1 Aylık Kişisel Özel Profil. Size özel PIN korumalı profil, 4K Ultra HD kalitesinde kesintisiz erişim. 30 gün boyunca tam lisans ve destek garantilidir. Otomatik teslimat.",
        "img_url": "https://bot-service-production-9d74.up.railway.app/static/disney_ozel_99.jpg",
        "local_img": "assets/products/disney_ozel_99.jpg",
        "category": "streaming",
        "category_label": "DİZİ & FİLM"
    },
    {
        "brand": "lisansarena",
        "key": "la_disney_ortak",
        "title": "Disney+ 1 Aylık Ortak Profil",
        "price": 69.90,
        "desc": "Disney+ 1 Aylık Ortak Profil Kullanımı. 4K Ultra HD, sınırsız dizi ve film keyfi. 30 gün kesintisiz telafi ve destek garantili. Otomatik anında teslimat.",
        "img_url": "https://bot-service-production-9d74.up.railway.app/static/disney_ortak_49.jpg",
        "local_img": "assets/products/disney_ortak_49.jpg",
        "category": "streaming",
        "category_label": "DİZİ & FİLM"
    },
    {
        "brand": "lisansarena",
        "key": "la_disney_ozel",
        "title": "Disney+ 1 Aylık Özel Profil",
        "price": 119.90,
        "desc": "Disney+ 1 Aylık Size Özel Profil. Size özel PIN korumalı profil, 4K Ultra HD kalitesi. 30 gün tam lisans ve destek güvencesi. Otomatik anında teslimat.",
        "img_url": "https://bot-service-production-9d74.up.railway.app/static/disney_ozel_99.jpg",
        "local_img": "assets/products/disney_ozel_99.jpg",
        "category": "streaming",
        "category_label": "DİZİ & FİLM"
    }
]

created_results = {}

for p in PRODUCTS_TO_CREATE:
    brand = p["brand"]
    token = tokens.get(brand)
    if not token:
        print(f"Token bulunamadı: {brand}")
        continue

    print(f"\n[{brand.upper()}] İlan oluşturuluyor: {p['title']} ({p['price']} TL)...")
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
                "url": p["img_url"],
                "placement": 1
            }
        ]
    }

    req = urllib.request.Request(
        "https://api.shopier.com/v1/products",
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            data = json.loads(r.read().decode('utf-8'))
            prod_id = str(data.get("id"))
            url = data.get("url") or f"https://www.shopier.com/{prod_id}"
            print(f"   BASARILI! ID: {prod_id} | URL: {url}")
            created_results[p["key"]] = {
                "id": prod_id,
                "url": url,
                "title": p["title"],
                "price": p["price"],
                "brand": brand,
                "desc": p["desc"],
                "local_img": p["local_img"],
                "category": p["category"],
                "category_label": p["category_label"]
            }
    except urllib.error.HTTPError as e:
        print(f"   HTTP Hatasi {e.code}: {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"   Hata: {e}")

with open("disney_created_shopier_listings.json", "w", encoding="utf-8") as f:
    json.dump(created_results, f, ensure_ascii=False, indent=2)

print("\nKaydedildi: disney_created_shopier_listings.json")
