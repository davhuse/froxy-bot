# -*- coding: utf-8 -*-
"""Create Shopier listings for Dijital Pazarım brand using Jarvis Shopier API."""

import json
import urllib.request
import ssl
import sys
from check_shopier_jwts import vars

sys.stdout.reconfigure(encoding='utf-8')

token = vars.get('SHOPIER_JARVIS_ACCESS_TOKEN')
if not token:
    print("SHOPIER_JARVIS_ACCESS_TOKEN bulunamadı!")
    sys.exit(1)

ctx = ssl._create_unverified_context()

BASE_IMG_URL = "https://raw.githubusercontent.com/davhuse/froxy-bot/main/static/"

# Pre-existing products already created on Shopier:
EXISTING_PRODUCTS = [
    {
        "id": "51358950",
        "key": "dp_disney_ortak_1m",
        "title": "Disney+ 1 Aylık Ortak Hesap",
        "price": "49.90 TL",
        "price_num": 49.90,
        "url": "https://www.shopier.com/51358950",
        "badge": "Fırsat",
        "category": "streaming",
        "category_label": "DİZİ & FİLM",
        "desc": "Disney+ 1 aylık ortak hesap erişimi. 4K Ultra HD kalitesinde, 30 gün telafi garantilidir. Otomatik teslimat.",
        "image": "assets/products/dp_disney_ortak.jpg"
    },
    {
        "id": "51358951",
        "key": "dp_disney_ozel_1m",
        "title": "Disney+ 1 Aylık Özel Profil",
        "price": "99.90 TL",
        "price_num": 99.90,
        "url": "https://www.shopier.com/51358951",
        "badge": "Özel Profil",
        "category": "streaming",
        "category_label": "DİZİ & FİLM",
        "desc": "Disney+ 1 aylık kişisel özel profil. Size özel PIN korumalı profil, 4K Ultra HD kalitesi, 30 gün garantili.",
        "image": "assets/products/dp_disney_ozel.jpg"
    }
]

PRODUCTS_TO_CREATE = [
    {
        "key": "dp_trendyol_go_800",
        "title": "Trendyol Go Market 800/300 İndirim Kuponu",
        "price": 44.99,
        "desc": "Trendyol Go Market 800 TL ve üzeri siparişlerde geçerli 300 TL indirim kupon kodu. Anında teslimat.",
        "category": "market",
        "category_label": "KUPON & MARKET",
        "badge": "300 TL İndirim",
        "img": BASE_IMG_URL + "dp_trendyol_go.jpg",
        "local_img": "assets/products/dp_trendyol_go.jpg"
    },
    {
        "key": "dp_trendyol_yemek_750",
        "title": "Trendyol Yemek 750/250 İndirim Kodu",
        "price": 44.99,
        "desc": "Trendyol Yemek 750 TL ve üzeri siparişlerde anında 250 TL indirim sağlayan kupon kodu. Anında teslimat.",
        "category": "market",
        "category_label": "YEMEK & KUPON",
        "badge": "250 TL İndirim",
        "img": BASE_IMG_URL + "dp_trendyol_yemek.jpg",
        "local_img": "assets/products/dp_trendyol_yemek.jpg"
    },
    {
        "key": "dp_shell_75",
        "title": "Shell 75 TL Akaryakıt Puan Kodu",
        "price": 19.99,
        "desc": "Shell istasyonlarında geçerli 75 TL akaryakıt veya otogaz indirim puan kodu. Anında teslimat.",
        "category": "market",
        "category_label": "YAKIT & ULAŞIM",
        "badge": "75 TL Puan",
        "img": BASE_IMG_URL + "dp_shell_75.jpg",
        "local_img": "assets/products/dp_shell_75.jpg"
    },
    {
        "key": "dp_uber_1000",
        "title": "Uber 1.000 TL İndirim Paketi (500+500 TL)",
        "price": 49.99,
        "desc": "Uber yolculuklarında geçerli 2 adet 500 TL toplam 1.000 TL indirim kupon kodu. Anında teslimat.",
        "category": "market",
        "category_label": "ULAŞIM",
        "badge": "1.000 TL Paket",
        "img": BASE_IMG_URL + "dp_uber_1000.jpg",
        "local_img": "assets/products/dp_uber_1000.jpg"
    },
    {
        "key": "dp_youtube_premium_3m",
        "title": "YouTube Premium 3 Aylık Bireysel Kod",
        "price": 49.99,
        "desc": "YouTube ve YouTube Music 3 aylık reklamsız bireysel kullanım kodu. Anında teslimat.",
        "category": "music",
        "category_label": "MÜZİK & VİDEO",
        "badge": "3 Aylık Kod",
        "img": BASE_IMG_URL + "dp_youtube_3m.jpg",
        "local_img": "assets/products/dp_youtube_3m.jpg"
    },
    {
        "key": "dp_spotify_premium_4m",
        "title": "Spotify Premium 4 Aylık Bireysel Kod",
        "price": 44.99,
        "desc": "Spotify Premium 4 aylık kesintisiz ve reklamsız müzik dinleme kodu. Anında teslimat.",
        "category": "music",
        "category_label": "MÜZİK & VİDEO",
        "badge": "4 Aylık Kod",
        "img": BASE_IMG_URL + "dp_spotify_4m.jpg",
        "local_img": "assets/products/dp_spotify_4m.jpg"
    },
    {
        "key": "dp_gemini_pro_18m_5inv",
        "title": "Gemini Pro 18 Ay (+5 Davet Hediyesi)",
        "price": 144.99,
        "desc": "Google Gemini Pro 18 aylık özel promosyon hesabı. 5 adet davet alma hakkı dahildir. 30 gün garantili.",
        "category": "ai",
        "category_label": "YAPAY ZEKA",
        "badge": "18 Ay + 5 Davet",
        "img": BASE_IMG_URL + "dp_gemini_18m_5inv.jpg",
        "local_img": "assets/products/dp_gemini_18m_5inv.jpg"
    },
    {
        "key": "dp_gemini_pro_18m_davet",
        "title": "Gemini Pro 18 Ay Davet Bağlantısı",
        "price": 74.99,
        "desc": "Google Gemini Pro 18 aylık kişisel davet bağlantısı. Kendi hesabınıza tanımlanır. Anında teslimat.",
        "category": "ai",
        "category_label": "YAPAY ZEKA",
        "badge": "18 Ay Davet",
        "img": BASE_IMG_URL + "dp_gemini_18m.jpg",
        "local_img": "assets/products/dp_gemini_18m.jpg"
    },
    {
        "key": "dp_gemini_pro_12m_davet",
        "title": "Gemini Pro 12 Ay Davet Bağlantısı",
        "price": 99.99,
        "desc": "Google Gemini Pro 12 aylık kişisel davet bağlantısı. Kendi hesabınıza tanımlanır. Anında teslimat.",
        "category": "ai",
        "category_label": "YAPAY ZEKA",
        "badge": "12 Ay Davet",
        "img": BASE_IMG_URL + "dp_gemini_12m.jpg",
        "local_img": "assets/products/dp_gemini_12m.jpg"
    },
    {
        "key": "dp_gemini_pro_1m_davet",
        "title": "Gemini Pro 1 Ay Davet Bağlantısı",
        "price": 49.99,
        "desc": "Google Gemini Pro 1 aylık hızlı başlangıç davet bağlantısı. Kendi hesabınıza tanımlanır.",
        "category": "ai",
        "category_label": "YAPAY ZEKA",
        "badge": "1 Ay Davet",
        "img": BASE_IMG_URL + "dp_gemini_1m.jpg",
        "local_img": "assets/products/dp_gemini_1m.jpg"
    },
    {
        "key": "dp_netflix_4k_ozel",
        "title": "Netflix 4K Ultra HD Kişisel Özel Profil",
        "price": 79.90,
        "desc": "Netflix 4K Ultra HD kişisel özel profil (30 Günlük). Kesintisiz erişim ve 30 gün tam telafi garantili.",
        "category": "streaming",
        "category_label": "DİZİ & FİLM",
        "badge": "4K UHD Profil",
        "img": BASE_IMG_URL + "dp_netflix_ozel.jpg",
        "local_img": "assets/products/dp_netflix_ozel.jpg"
    }
]

created_results = list(EXISTING_PRODUCTS)

for idx, p in enumerate(PRODUCTS_TO_CREATE):
    print(f"\n[{idx+1}/{len(PRODUCTS_TO_CREATE)}] Shopier ilanı oluşturuluyor: {p['title']} ({p['price']} TL)...")
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
                "url": p["img"],
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
            print(f"   BAŞARILI! ID: {prod_id} | URL: {url}")
            created_results.append({
                "id": prod_id,
                "key": p["key"],
                "title": p["title"],
                "price": f"{p['price']:.2f} TL".replace(".", ","),
                "price_num": p["price"],
                "url": url,
                "badge": p["badge"],
                "category": p["category"],
                "category_label": p["category_label"],
                "desc": p["desc"],
                "image": p["local_img"]
            })
    except urllib.error.HTTPError as e:
        print(f"   HTTP Hatası {e.code}: {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"   Hata: {e}")

# Save to dijitalpazarim_shopier_products.json and miniapp_dijitalpazarim/products_db.json
with open("dijitalpazarim_shopier_products.json", "w", encoding="utf-8") as f:
    json.dump(created_results, f, ensure_ascii=False, indent=2)

with open("miniapp_dijitalpazarim/products_db.json", "w", encoding="utf-8") as f:
    json.dump(created_results, f, ensure_ascii=False, indent=2)

print(f"\nTamamlandı! Toplam aktif Dijital Pazarım ilanı: {len(created_results)}")
