import urllib.request
import urllib.parse
import urllib.error
import json
import ssl
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJiOGI0MjA0NWM1NDY2ZDdiMWQwODc0OGUzZTBkNDlmNSIsImp0aSI6ImY1YmQ1Yzk4Y2U3NmEwNWIyNDhiYTNmY2Q3MThjN2YzNjgwNzE2Y2M4ODhkNWM5ZWZjNzIzNmY0MDA3YmZiNjA1MmEwOTlmYWJlZWY5Y2I0NzgxMjY4OWI4YWM0NTI3MmE4NmNmZGNkMjU0YTJjNThjYTdhMzc0MjNhMjE5ZGQzNjNhM2FjMmM3YTFhZTFiZTY4OWRmODI1MmUzMDE0MjMiLCJpYXQiOjE3ODU1MjA4MDUsIm5iZiI6MTc4NTUyMDgwNSwiZXhwIjoxOTQzMzA1NTY1LCJzdWIiOjI1MDk0OTMsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.MjmL2Y8Eapk8FYETmZbcdo0sYqAseKPu1I0qGKiMOHCYrlKqWsC53IOnzf8WiZEeUvHAFDxqmqmEGuo5x_Xx6ncMX_8sj0VXzkaEOl5EnGjeq3qbwkGOhXxUT7d914qMTELeku0AysnPQdOiGgot-pSh2XMl86YEtTJmLD1qjQd9uG5VPbzcjcHxYUf18WZ6beZf7974xAo-36rJK2F0nZ1JvWaGZz-lG0XyEGh50HQIyBPwSkCb85pJEKbPa_n-iTR5D1eMwQyGkWMT2IpHQ8PHtUaDIK-S5UNTlWEPLxUDYQevnJ13ajGjpXVVXONURCYD2WbtCvWciGWyNqyJ8Q"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

brain_dir = r"C:\Users\habil\.gemini\antigravity\brain\ed3941df-49b3-4746-98df-0ef5ef475eb2"

PRODUCTS = [
    {
        "title": "Prime Video 30 Günlük (Ortak Hesap)",
        "price": "9.99",
        "desc": "Amazon Prime Video 30 Günlük Ortak Kullanım Hesabı. Otomatik teslimat.",
        "img": "keyvadi_banner.png"
    },
    {
        "title": "Netflix 4K Ultra HD Kişisel Profil",
        "price": "79.99",
        "desc": "Netflix 4K Ultra HD Kişisel Özel Profil (30 Günlük). Otomatik teslimat.",
        "img": "netflix_4k_keyvadi_banner_1785520241849.jpg"
    },
    {
        "title": "Canva Pro (1 Yıl Yetki)",
        "price": "49.99",
        "desc": "Canva Pro 1 Yıllık Davet Yetkisi. Kendi kişisel hesabınıza tanımlanır.",
        "img": "canva_pro_keyvadi_banner_1785520255556.jpg"
    },
    {
        "title": "CapCut Pro (1 Aylık Kişisel)",
        "price": "199.99",
        "desc": "CapCut Pro 1 Aylık Bireysel Kişisel Lisans Hesabı. 4K ve pro efektler açıktır.",
        "img": "capcut_pro_keyvadi_banner_1785520230354.jpg"
    },
    {
        "title": "CapCut Pro (1 Aylık Ortak Hesap)",
        "price": "49.99",
        "desc": "CapCut Pro 1 Aylık Ortak Kullanım Hesabı. Tüm pro özellikler aktiftir.",
        "img": "capcut_pro_keyvadi_banner_1785520230354.jpg"
    },
    {
        "title": "Trendyol Market Kuponu (800₺/300₺ İndirim)",
        "price": "49.99",
        "desc": "Trendyol Market 800 TL Siparişe 300 TL İndirim Sağlayan Kupon Kodu.",
        "img": "trendyol_market_keyvadi_banner_1785521363461.jpg"
    },
    {
        "title": "Trendyol Yemek Kuponu (700₺/250₺ İndirim)",
        "price": "49.99",
        "desc": "Trendyol Yemek 700 TL Siparişe 250 TL İndirim Sağlayan Kupon Kodu.",
        "img": "trendyol_yemek_keyvadi_banner_1785521352313.jpg"
    },
    {
        "title": "Steam İstediğiniz Oyun (Ortak Hesap)",
        "price": "30.00",
        "desc": "Steam platformunda dilediğiniz oyunun Ortak Kullanım Hesabı. Otomatik teslimat.",
        "img": "steam_isteginiz_oyun_banner_1785521528961.jpg"
    },
    {
        "title": "Xbox Game Pass Ultimate (1 Ay Ortak Hesap)",
        "price": "49.99",
        "desc": "Xbox Game Pass Ultimate 1 Aylık Ortak Kullanım Hesabı. PC ve Konsol uyumludur.",
        "img": "xbox_game_pass_1m_banner_1785521541671.jpg"
    }
]

def upload_image_tmpfiles(filepath):
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    with open(filepath, 'rb') as f:
        img_bytes = f.read()

    filename = os.path.basename(filepath)
    body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f'Content-Type: image/jpeg\r\n\r\n'
    ).encode('utf-8') + img_bytes + f'\r\n--{boundary}--\r\n'.encode('utf-8')

    req = urllib.request.Request('https://tmpfiles.org/api/v1/upload', data=body, headers={
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'User-Agent': 'Mozilla/5.0'
    })
    with urllib.request.urlopen(req, context=ctx) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        page_url = res.get('data', {}).get('url', '')
        return page_url.replace('tmpfiles.org/', 'tmpfiles.org/dl/')

print("=" * 70)
print("🚀 SHOPIER REST API İLE DOĞRUDAN İLAN OLUŞTURUCU")
print("=" * 70)

created_results = []

for idx, p in enumerate(PRODUCTS):
    print(f"\n[{idx+1}/{len(PRODUCTS)}] İşleniyor: {p['title']} ({p['price']} TL)...")
    
    # 1. Image path
    img_path = os.path.join(brain_dir, p['img'])
    if not os.path.exists(img_path):
        img_path = os.path.join(os.getcwd(), 'static', p['img'])

    direct_img_url = ""
    if os.path.exists(img_path):
        try:
            direct_img_url = upload_image_tmpfiles(img_path)
            print(f"   🖼️ Görsel CDN Yüklendi: {direct_img_url}")
        except Exception as ie:
            print(f"   ⚠️ Görsel CDN yükleme hatası: {ie}")

    payload = {
        "title": p["title"],
        "type": "digital",
        "description": p["desc"],
        "priceData": {
            "currency": "TRY",
            "price": p["price"],
            "discount": False,
            "discountedPrice": p["price"],
            "shippingPrice": "0.00"
        },
        "stockQuantity": 999,
        "shippingPayer": "sellerPays"
    }

    if direct_img_url:
        payload["media"] = [
            {
                "type": "image",
                "url": direct_img_url,
                "placement": 1
            }
        ]

    req = urllib.request.Request('https://api.shopier.com/v1/products', data=json.dumps(payload).encode('utf-8'), headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    })

    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            pid = res.get('id')
            p_url = f"https://www.shopier.com/keyvadi/{pid}"
            print(f"   ✅ BAŞARIYLA OLUŞTURULDU! İlan ID: {pid} | Link: {p_url}")
            created_results.append({'title': p['title'], 'id': pid, 'url': p_url, 'price': p['price']})
    except urllib.error.HTTPError as e:
        print(f"   ❌ API Hatası (HTTP {e.code}): {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"   ❌ Hata: {e}")

print("\n" + "=" * 70)
print(f"TOPLAM OLUŞTURULAN SHOPIER İLANI: {len(created_results)}")
print("=" * 70)

with open('created_keyvadi_shopier_products.json', 'w', encoding='utf-8') as f:
    json.dump(created_results, f, ensure_ascii=False, indent=2)
