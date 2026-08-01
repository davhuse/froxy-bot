import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

keyvadi_products = [
    {
        "id": "47669321",
        "title": "Canva Pro (1 Yıl Yetki)",
        "type": "digital",
        "url": "https://www.shopier.com/keyvadi/47669321",
        "priceData": {"currency": "TRY", "price": "49.99"},
        "description": "Canva Pro 1 Yıllık Davet Yetkisi."
    },
    {
        "id": "49002145",
        "title": "Prime Video 30 Günlük (Ortak Hesap)",
        "type": "digital",
        "url": "https://www.shopier.com/49002145",
        "priceData": {"currency": "TRY", "price": "9.99"},
        "description": "Amazon Prime Video 30 Günlük Ortak Kullanım Hesabı."
    },
    {
        "id": "49362708",
        "title": "Gemini Pro (3 Ay Davet)",
        "type": "digital",
        "url": "https://www.shopier.com/49362708",
        "priceData": {"currency": "TRY", "price": "59.90"},
        "description": "Gemini Pro 3 Aylık Davet Hesabı."
    },
    {
        "id": "47669164",
        "title": "Gemini Pro (12 Ay Davet)",
        "type": "digital",
        "url": "https://www.shopier.com/keyvadi/47669164",
        "priceData": {"currency": "TRY", "price": "69.99"},
        "description": "Gemini Pro 12 Aylık Davet Hesabı."
    },
    {
        "id": "47669222",
        "title": "Gemini Ultra (2.5K Kredili)",
        "type": "digital",
        "url": "https://www.shopier.com/keyvadi/47669222",
        "priceData": {"currency": "TRY", "price": "599.99"},
        "description": "Gemini Ultra 2.5K Kredi Yüklü Özel Hesap."
    },
    {
        "id": "47669117",
        "title": "Netflix 4K UHD Kişisel Profil",
        "type": "digital",
        "url": "https://www.shopier.com/47669117",
        "priceData": {"currency": "TRY", "price": "79.99"},
        "description": "Netflix 4K Ultra HD Kişisel Özel Profil (30 Günlük)."
    },
    {
        "id": "47669154",
        "title": "ChatGPT Plus (1 Aylık Kişisel)",
        "type": "digital",
        "url": "https://www.shopier.com/keyvadi/47669154",
        "priceData": {"currency": "TRY", "price": "250.00"},
        "description": "ChatGPT Plus 1 Aylık Kişisel Özel Hesap."
    },
    {
        "id": "49362861",
        "title": "ChatGPT Plus (1 Aylık Ortak)",
        "type": "digital",
        "url": "https://www.shopier.com/49362861",
        "priceData": {"currency": "TRY", "price": "69.90"},
        "description": "ChatGPT Plus 1 Aylık Ortak Kullanım Hesabı."
    },
    {
        "id": "47669248",
        "title": "Super Grok / X Premium (1 Ay)",
        "type": "digital",
        "url": "https://www.shopier.com/keyvadi/47669248",
        "priceData": {"currency": "TRY", "price": "449.99"},
        "description": "Super Grok / X Premium 1 Aylık Üyelik."
    },
    {
        "id": "48943136",
        "title": "Perplexity Pro (1 Aylık)",
        "type": "digital",
        "url": "https://www.shopier.com/48943136",
        "priceData": {"currency": "TRY", "price": "119.90"},
        "description": "Perplexity Pro 1 Aylık Hesap."
    },
    {
        "id": "48943139",
        "title": "DeepL AI Pro (1 Aylık Ortak)",
        "type": "digital",
        "url": "https://www.shopier.com/48943139",
        "priceData": {"currency": "TRY", "price": "29.90"},
        "description": "DeepL AI Pro Çeviri Ortak Hesap."
    },
    {
        "id": "47669369",
        "title": "CapCut Pro (1 Aylık Kişisel)",
        "type": "digital",
        "url": "https://www.shopier.com/keyvadi/47669369",
        "priceData": {"currency": "TRY", "price": "199.99"},
        "description": "CapCut Pro 1 Aylık Kişisel Bireysel Hesap."
    },
    {
        "id": "47669369_ortak",
        "title": "CapCut Pro (1 Aylık Ortak Hesap)",
        "type": "digital",
        "url": "https://www.shopier.com/keyvadi/47669369",
        "priceData": {"currency": "TRY", "price": "49.99"},
        "description": "CapCut Pro 1 Aylık Ortak Kullanım Hesabı."
    },
    {
        "id": "47669486",
        "title": "Trendyol Market (800₺'ye 300₺ İndirim)",
        "type": "digital",
        "url": "https://www.shopier.com/keyvadi/47669486",
        "priceData": {"currency": "TRY", "price": "49.99"},
        "description": "Trendyol Market 800 TL Siparişe 300 TL İndirim Kuponu."
    },
    {
        "id": "47669482",
        "title": "Trendyol Yemek (700₺'ye 250₺ İndirim)",
        "type": "digital",
        "url": "https://www.shopier.com/keyvadi/47669482",
        "priceData": {"currency": "TRY", "price": "49.99"},
        "description": "Trendyol Yemek 700 TL Siparişe 250 TL İndirim Kuponu."
    },
    {
        "id": "48114807",
        "title": "Xbox Game Pass 1 Ay (Ortak Hesap)",
        "type": "digital",
        "url": "https://www.shopier.com/keyvadi/48114807",
        "priceData": {"currency": "TRY", "price": "49.99"},
        "description": "Xbox Game Pass Ultimate 1 Aylık Ortak Hesap."
    },
    {
        "id": "48114802",
        "title": "Steam İstediğiniz Oyun (Ortak Hesap)",
        "type": "digital",
        "url": "https://www.shopier.com/keyvadi/48114802",
        "priceData": {"currency": "TRY", "price": "30.00"},
        "description": "Steam Dilediğiniz Oyun Ortak Kullanım Hesabı."
    },
    {
        "id": "48114785",
        "title": "Windows 10/11 Pro Lisans Anahtarı (Key)",
        "type": "digital",
        "url": "https://www.shopier.com/keyvadi/48114785",
        "priceData": {"currency": "TRY", "price": "70.00"},
        "description": "Windows 10/11 Pro Orijinal Lisans Anahtarı."
    },
    {
        "id": "48114785_office",
        "title": "Office 365 1 Yıllık Lisans",
        "type": "digital",
        "url": "https://www.shopier.com/keyvadi/48114785",
        "priceData": {"currency": "TRY", "price": "70.00"},
        "description": "Microsoft Office 365 1 Yıllık Lisans Hesabı."
    },
    {
        "id": "47669496",
        "title": "Shell 75 TL Akaryakıt Puanı",
        "type": "digital",
        "url": "https://www.shopier.com/keyvadi/47669496",
        "priceData": {"currency": "TRY", "price": "14.99"},
        "description": "Shell 75 TL Akaryakıt Puan Kodu."
    },
    {
        "id": "48943133",
        "title": "Eski Tarihli Telegram Hesabı (+1 No'lu)",
        "type": "digital",
        "url": "https://www.shopier.com/48943133",
        "priceData": {"currency": "TRY", "price": "149.90"},
        "description": "Eski Tarihli Onaylı Telegram Hesabı."
    }
]

with open("keyvadi_shopier_links.json", "w", encoding="utf-8") as f:
    json.dump(keyvadi_products, f, ensure_ascii=False, indent=2)

print(f"SUCCESS: Rewrote keyvadi_shopier_links.json with {len(keyvadi_products)} clean KeyVadi products!")
