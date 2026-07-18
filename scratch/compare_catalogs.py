import json

# KeyVadi full product list (from froxy_bot.py INJECTED_PRODUCTS)
keyvadi_products = [
    {"id": "47669105", "title": "YouTube Premium (3 Aylık Kod)", "price": "29.99"},
    {"id": "47669117", "title": "Netflix 4K Ultra HD (Kişisel Profil)", "price": "49.99"},
    {"id": "48114807", "title": "XBOX Game Pass Ultimate (3 Aylık Üyelik)", "price": "80.00"},
    {"id": "48114802", "title": "Steam İstediğiniz Oyun (60 TL Limitli)", "price": "60.00"},
    {"id": "48114795", "title": "Semrush Pro (14 Günlük Hesap)", "price": "150.00"},
    {"id": "48114789", "title": "Microsoft Office 365 (1 Yıllık Hesap)", "price": "70.00"},
    {"id": "48114785", "title": "Windows 10/11 Pro Lisans Anahtarı (Key)", "price": "70.00"},
    {"id": "47669159", "title": "Gemini Pro (1 Yıllık Hesap)", "price": "299.99"},
    {"id": "47669164", "title": "Gemini Pro (Davet Linki)", "price": "124.99"},
    {"id": "47669192", "title": "Gemini Ultra (Davet Linki)", "price": "399.99"},
    {"id": "47669222", "title": "Gemini Ultra (2.5k Kredili Hesap)", "price": "599.99"},
    {"id": "47669248", "title": "Super Grok (1 Aylık Hesap)", "price": "449.99"},
    {"id": "47669271", "title": "Super Grok (3 Aylık Hesap)", "price": "949.99"},
    {"id": "47669295", "title": "Super Grok (6 Aylık Hesap)", "price": "1499.99"},
    {"id": "47669305", "title": "Super Grok (12 Aylık Hesap)", "price": "2299.99"},
    {"id": "47669310", "title": "Gamma Ultra (1 Aylık Hesap)", "price": "449.99"},
    {"id": "47669316", "title": "Gamma Pro (1 Aylık Hesap)", "price": "299.99"},
    {"id": "48943133", "title": "Eski Tarihli Telegram Hesabı (+1 No'lu)", "price": "149.90"},
    {"id": "48943136", "title": "Perplexity Pro (1 Aylık Hesap)", "price": "119.90"},
    {"id": "48943137", "title": "DeepL AI (1 Aylık) - Kişisel Hesap", "price": "59.90"},
    {"id": "48943139", "title": "DeepL AI (1 Aylık) - Ortak Hesap", "price": "29.90"},
    {"id": "48943141", "title": "Scribd (1 Aylık) - Kişisel Hesap", "price": "59.90"},
    {"id": "48943143", "title": "Scribd (1 Aylık) - Ortak Hesap", "price": "29.90"},
    {"id": "48943144", "title": "Magnific AI Ortak (1 Aylık Business Hesap)", "price": "49.90"},
    {"id": "48943146", "title": "Crunchyroll Özel Profil (1 Aylık)", "price": "59.90"},
    {"id": "48943148", "title": "Crunchyroll Ortak Hesap (1 Aylık)", "price": "39.90"},
    {"id": "48943150", "title": "Grammarly Pro (1 Haftalık) - Kendi Hesabınıza", "price": "79.90"},
    {"id": "48943151", "title": "Grammarly Pro (1 Aylık) - Ortak Hesap", "price": "49.90"},
]

# Load existing LisansArena catalog
with open("lisansarena_shopier_links.json", "r", encoding="utf-8") as f:
    lisansarena = json.load(f)

existing_titles = set()
for p in lisansarena:
    existing_titles.add(p["title"].strip().lower())

print(f"LisansArena'da mevcut urun sayisi: {len(lisansarena)}")
print(f"KeyVadi'de toplam urun sayisi: {len(keyvadi_products)}")
print()

missing = []
for kv in keyvadi_products:
    t = kv["title"].strip().lower()
    if t not in existing_titles:
        missing.append(kv)
        print(f"EKSIK: {kv['title']} | KV fiyat: {kv['price']} TL | LA fiyat (%5): {round(float(kv['price']) * 1.05, 2)} TL")

print(f"\nToplam eksik urun: {len(missing)}")
