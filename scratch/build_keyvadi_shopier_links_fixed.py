import json
import os

parsed_path = "parsed_keyvadi_products.json"
target_path = "keyvadi_shopier_links.json"

# Base products from parsed file
products = []
if os.path.exists(parsed_path):
    with open(parsed_path, "r", encoding="utf-8") as f:
        products = json.load(f)

# All injected and missing products for KeyVadi
all_extra_products = [
    {"id": "47669105", "title": "YouTube Premium (3 Aylık Kod)", "price": "29.99 TL", "url": "https://www.shopier.com/keyvadi/47669105"},
    {"id": "47669117", "title": "Netflix 4K Ultra HD (Kişisel Profil)", "price": "49.99 TL", "url": "https://www.shopier.com/keyvadi/47669117"},
    {"id": "48114807", "title": "XBOX Game Pass Ultimate (3 Aylık Üyelik)", "price": "80.00 TL", "url": "https://www.shopier.com/keyvadi/48114807"},
    {"id": "48114802", "title": "Steam İstediğiniz Oyun (60 TL Limitli)", "price": "60.00 TL", "url": "https://www.shopier.com/keyvadi/48114802"},
    {"id": "48114795", "title": "Semrush Pro (14 Günlük Hesap)", "price": "150.00 TL", "url": "https://www.shopier.com/keyvadi/48114795"},
    {"id": "48114789", "title": "Microsoft Office 365 (1 Yıllık Hesap)", "price": "70.00 TL", "url": "https://www.shopier.com/keyvadi/48114789"},
    {"id": "48114785", "title": "Windows 10/11 Pro Lisans Anahtarı (Key)", "price": "70.00 TL", "url": "https://www.shopier.com/keyvadi/48114785"},
    {"id": "47669159", "title": "Gemini Pro (1 Yıllık Hesap)", "price": "299.99 TL", "url": "https://www.shopier.com/keyvadi/47669159"},
    {"id": "47669164", "title": "Gemini Pro (Davet Linki)", "price": "124.99 TL", "url": "https://www.shopier.com/keyvadi/47669164"},
    {"id": "47669192", "title": "Gemini Ultra (Davet Linki)", "price": "399.99 TL", "url": "https://www.shopier.com/keyvadi/47669192"},
    {"id": "47669222", "title": "Gemini Ultra (2.5k Kredili Hesap)", "price": "599.99 TL", "url": "https://www.shopier.com/keyvadi/47669222"},
    {"id": "47669248", "title": "Super Grok (1 Aylık Hesap)", "price": "449.99 TL", "url": "https://www.shopier.com/keyvadi/47669248"},
    {"id": "47669271", "title": "Super Grok (3 Aylık Hesap)", "price": "949.99 TL", "url": "https://www.shopier.com/keyvadi/47669271"},
    {"id": "47669295", "title": "Super Grok (6 Aylık Hesap)", "price": "1499.99 TL", "url": "https://www.shopier.com/keyvadi/47669295"},
    {"id": "47669305", "title": "Super Grok (12 Aylık Hesap)", "price": "2299.99 TL", "url": "https://www.shopier.com/keyvadi/47669305"},
    {"id": "47669310", "title": "Gamma Ultra (1 Aylık Hesap)", "price": "449.99 TL", "url": "https://www.shopier.com/keyvadi/47669310"},
    {"id": "47669316", "title": "Gamma Pro (1 Aylık Hesap)", "price": "299.99 TL", "url": "https://www.shopier.com/keyvadi/47669316"},
    {"id": "47669321", "title": "Canva Pro (1 Yıllık Yetki)", "price": "83.99 TL", "url": "https://www.shopier.com/keyvadi/47669321"},
    {"id": "49002143", "title": "HBO Max 1 Aylık Profil", "price": "39.90 TL", "url": "https://www.shopier.com/49002143"},
    {"id": "49002144", "title": "Prime Video (1 Aylık) - Özel Profil", "price": "29.90 TL", "url": "https://www.shopier.com/49002144"},
    {"id": "49002145", "title": "Prime Video (1 Aylık) - Ortak Profil", "price": "19.90 TL", "url": "https://www.shopier.com/49002145"}
]

# Avoid duplicates and merge cleanly
existing_ids = {p["id"] for p in products}
for xp in all_extra_products:
    if xp["id"] not in existing_ids:
        products.append(xp)
    else:
        # Update URL or title if already present but needs latest
        for p in products:
            if p["id"] == xp["id"]:
                p["url"] = xp["url"]
                p["title"] = xp["title"]
                break

# Save both keyvadi_shopier_links.json and parsed_keyvadi_products.json
with open(target_path, "w", encoding="utf-8") as f:
    json.dump(products, f, indent=2, ensure_ascii=False)

with open(parsed_path, "w", encoding="utf-8") as f:
    json.dump(products, f, indent=2, ensure_ascii=False)

print(f"Successfully generated database with {len(products)} products!")
