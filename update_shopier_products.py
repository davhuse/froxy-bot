import os
import sys
import json
import urllib.request
import urllib.error
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# List of updated products for KeyVadi Shopier store
PRODUCTS_TO_UPDATE = [
    {
        "name": "Prime Video (30 Günlük Ortak Hesap)",
        "price": 9.99,
        "desc": "Amazon Prime Video 30 Günlük Ortak Kullanım Hesabı. Otomatik teslimat.",
        "slug": "prime_video_ortak"
    },
    {
        "name": "Netflix 4K Ultra HD Kişisel Profil",
        "price": 79.99,
        "desc": "Netflix 4K Ultra HD Kişisel Özel Profil (30 Günlük). Otomatik teslimat.",
        "slug": "netflix_4k"
    },
    {
        "name": "Canva Pro (1 Yıl Yetki)",
        "price": 49.99,
        "desc": "Canva Pro 1 Yıllık Davet Yetkisi. Kendi hesabınızda tanımlanır.",
        "slug": "canva"
    },
    {
        "name": "CapCut Pro (1 Aylık Kişisel)",
        "price": 199.99,
        "desc": "CapCut Pro 1 Aylık Bireysel Kişisel Lisans Hesabı. 4K export ve tüm efektler aktif.",
        "slug": "capcut_kisisel"
    },
    {
        "name": "CapCut Pro (1 Aylık Ortak Hesap)",
        "price": 49.99,
        "desc": "CapCut Pro 1 Aylık Ortak Kullanım Hesabı. Tüm pro özellikler açıktır.",
        "slug": "capcut_ortak"
    },
    {
        "name": "Trendyol Market İndirim Kuponu (800₺/300₺)",
        "price": 49.99,
        "desc": "Trendyol Market 800 TL Siparişe 300 TL İndirim Sağlayan Kupon Kodu.",
        "slug": "trendyol_market"
    },
    {
        "name": "Yemeksepeti İndirim Kuponu (750₺/250₺)",
        "price": 49.99,
        "desc": "Yemeksepeti 750 TL Siparişe 250 TL İndirim Sağlayan Kupon Kodu.",
        "slug": "yemeksepeti"
    },
    {
        "name": "Steam İstediğiniz Oyun (Ortak Hesap)",
        "price": 30.00,
        "desc": "Steam platformunda dilediğiniz oyunun Ortak Kullanım Hesabı. Otomatik teslimat.",
        "slug": "steam_oyun"
    },
    {
        "name": "Xbox Game Pass Ultimate (1 Ay Ortak Hesap)",
        "price": 49.99,
        "desc": "Xbox Game Pass Ultimate 1 Aylık Ortak Kullanım Hesabı. PC ve Konsol uyumlu.",
        "slug": "xbox_game_pass"
    }
]

def update_via_api(token):
    print("=" * 60)
    print("SHOPIER REST API İLE İLANLARI OLUŞTURMA / GÜNCELLEME")
    print("=" * 60)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Authorization": f"Bearer {token.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # 1. Fetch existing products
    try:
        req = urllib.request.Request("https://api.shopier.com/v1/products", headers=headers)
        with urllib.request.urlopen(req, context=ctx) as resp:
            existing = json.loads(resp.read().decode('utf-8'))
            print(f"✅ Mevcut Shopier Ürün Sayısı: {len(existing)}")
    except Exception as e:
        print(f"❌ Shopier API Erişimi Başarısız: {e}")
        return False

    # Map by title
    existing_map = {p.get("title", "").strip().lower(): p for p in existing}

    for p in PRODUCTS_TO_UPDATE:
        title = p["name"]
        price_str = f"{p['price']:.2f}"
        desc = p["desc"]
        
        match = existing_map.get(title.lower())
        if match:
            pid = match.get("id")
            print(f"🔄 Güncelleniyor: {title} (ID: {pid}) -> Fiyat: {price_str} TL")
            put_payload = {
                "title": title,
                "description": desc,
                "type": "digital",
                "priceData": {
                    "currency": "TRY",
                    "price": price_str,
                    "discount": False,
                    "discountedPrice": price_str,
                    "shippingPrice": "0.00"
                },
                "stockQuantity": 999
            }
            try:
                put_req = urllib.request.Request(
                    f"https://api.shopier.com/v1/products/{pid}",
                    data=json.dumps(put_payload).encode('utf-8'),
                    headers=headers,
                    method="PUT"
                )
                with urllib.request.urlopen(put_req, context=ctx) as resp:
                    print(f"   ✅ {title} başarıyla güncellendi!")
            except Exception as pe:
                print(f"   ⚠️ Güncelleme hatası: {pe}")
        else:
            print(f"➕ Yeni Oluşturuluyor: {title} -> Fiyat: {price_str} TL")
            post_payload = {
                "title": title,
                "description": desc,
                "type": "digital",
                "priceData": {
                    "currency": "TRY",
                    "price": price_str,
                    "discount": False,
                    "discountedPrice": price_str,
                    "shippingPrice": "0.00"
                },
                "stockQuantity": 999
            }
            try:
                post_req = urllib.request.Request(
                    "https://api.shopier.com/v1/products",
                    data=json.dumps(post_payload).encode('utf-8'),
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(post_req, context=ctx) as resp:
                    res_data = json.loads(resp.read().decode('utf-8'))
                    print(f"   ✅ {title} başarıyla oluşturuldu! (ID: {res_data.get('id')})")
            except Exception as pe:
                print(f"   ⚠️ Oluşturma hatası: {pe}")

    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        tok = sys.argv[1].strip()
        update_via_api(tok)
    else:
        print("Kullanım: python update_shopier_products.py <SHOPIER_BEARER_TOKEN>")
