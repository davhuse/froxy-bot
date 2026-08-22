# -*- coding: utf-8 -*-
import json

TITLE_FIXES = {
    # KeyVadi & LisansArena Title Corrections
    "Canva Pro retmen (1 Yllk)": "Canva Pro Öğretmen (1 Yıllık)",
    "Canva Pro retmen (1 Yllk Lisans)": "Canva Pro Öğretmen (1 Yıllık Lisans)",
    "Canva Pro renci (1 Yllk Lisans)": "Canva Pro Öğrenci (1 Yıllık Lisans)",
    "Canva Pro (1 Yllk Yetki & zel Lisans)": "Canva Pro (1 Yıllık Yetki & Özel Lisans)",
    "Canva Pro 1 Yl - Kendi Hesabna Davet": "Canva Pro 1 Yıl - Kendi Hesabına Davet",
    "YouTube Premium (3 Aylk Kod)": "YouTube Premium (3 Aylık Kod)",
    "YouTube Premium (3 Aylk Lisans Kodu)": "YouTube Premium (3 Aylık Lisans Kodu)",
    "YouTube Premium 1 Ay - Kendi Hesabna Davet": "YouTube Premium 1 Ay - Kendi Hesabına Davet",
    "Netflix 4K Ultra HD (Kiisel Profil)": "Netflix 4K Ultra HD (Kişisel Profil)",
    "Netflix 4K UHD (zel Kiisel Profil)": "Netflix 4K UHD (Özel Kişisel Profil)",
    "ChatGPT Plus 30 Gn - Kiisel": "ChatGPT Plus 30 Gün - Kişisel",
    "ChatGPT Plus 30 Gn - Ortak Hesap": "ChatGPT Plus 30 Gün - Ortak Hesap",
    "Gemini Advanced Pro 3 Ay - Davet Balants": "Gemini Advanced Pro 3 Ay - Davet Bağlantısı",
    "Gemini Pro 18 Ay - Davet Balants": "Gemini Pro 18 Ay - Davet Bağlantısı",
    "Gemini Pro (1 Yllk Hesap)": "Gemini Pro (1 Yıllık Hesap)",
    "Gemini Pro Davet (12 Aylk Lisans)": "Gemini Pro Davet (12 Aylık Lisans)",
    "Gemini Ultra (Davet Linki - 12 Aylk)": "Gemini Ultra (Davet Linki - 12 Aylık)",
    "Gemini Pro Premium Hesap (12 Aylk)": "Gemini Pro Premium Hesap (12 Aylık)",
    "Spotify Premium (4 Aylk Kod)": "Spotify Premium (4 Aylık Kod)",
    "Spotify Premium (3 Aylk Davet & Kod)": "Spotify Premium (3 Aylık Davet & Kod)",
    "Exxen Reklamsz (3 Aylk)": "Exxen Reklamsız (3 Aylık)",
    "Exxen Reklamsz (3 Aylk Lisans Kodu)": "Exxen Reklamsız (3 Aylık Lisans Kodu)",
    "FC 26 Hesab - Bilgileri Deitirilebilir": "FC 26 Hesabı - Bilgileri Değiştirilebilir",
    "FC26 + Online Her eyi Deien Hesap": "FC 26 + Online Her Şeyi Değişen Hesap",
    "Steam 200 Dolar Random Key": "Steam 200$ Değerinde VIP Random Key",
    "Steam 200$ Deerinde VIP Random Key": "Steam 200$ Değerinde VIP Random Key",
    "Steam 45$ Deerinde Random Key": "Steam 45$ Değerinde Random Key",
    "Steam stediiniz Oyun (Ortak Hesap)": "Steam İstediğiniz Oyun (Ortak Hesap)",
    "CapCut Pro (1 Aylk Kiisel)": "CapCut Pro (1 Aylık Kişisel)",
    "CapCut Pro (1 Aylk Kiisel Lisans)": "CapCut Pro (1 Aylık Kişisel Lisans)",
    "CapCut Pro (1 Aylk Ortak Hesap)": "CapCut Pro (1 Aylık Ortak Hesap)",
    "CapCut Pro (1 Aylk Ortak)": "CapCut Pro (1 Aylık Ortak)",
    "CapCut Pro (1 Haftalk Hesap)": "CapCut Pro (1 Haftalık Hesap)",
    "XBOX Game Pass Ultimate (3 Aylk yelik)": "Xbox Game Pass Ultimate (3 Aylık Üyelik)",
    "Xbox Game Pass Ultimate (1 Ay Ortak Hesap)": "Xbox Game Pass Ultimate (1 Aylık Ortak)",
    "Duolingo Super - Snf Daveti": "Duolingo Super - Sınıf Daveti",
    "Super Duolingo Snrsz (Ortak Hesap)": "Super Duolingo Sınırsız (Ortak Hesap)",
    "Discord Nitro Server Boost (1 Aylk 14X Takviye Paket)": "Discord Nitro Server Boost (1 Aylık 14X Takviye Paketi)",
    "Windows 10/11 Pro Lisans Anahtar (Key)": "Windows 10/11 Pro Orijinal Lisans Anahtarı",
    "Windows 10 / 11 Pro Orijinal Lisans Key": "Windows 10/11 Pro Orijinal Lisans Anahtarı",
    "Microsoft Office 365 (1 Yllk Hesap)": "Microsoft Office 365 (1 Yıllık Hesap)",
    "Kaspersky Premium 1 Yl / 1 Cihaz": "Kaspersky Premium (1 Yıl / 1 Cihaz)",
    "Prime Video (1 Aylk) - Ortak Profil": "Prime Video (1 Aylık) - Ortak Profil",
    "Prime Video (1 Aylk) - zel Profil": "Prime Video (1 Aylık) - Özel Profil",
    "Amazon Prime Video 4K (zel Profil)": "Amazon Prime Video 4K (Özel Profil)",
    "HBO Max 1 Aylk Profil": "HBO Max (1 Aylık Özel Profil)",
    "HBO Max zel Plan (1 Aylk Profil)": "HBO Max Özel Plan (1 Aylık Profil)",
    "Grammarly Pro (1 Aylk) - Ortak Hesap": "Grammarly Pro (1 Aylık) - Ortak Hesap",
    "Grammarly Pro (1 Haftalk) - Kendi Hesabnza": "Grammarly Pro (1 Haftalık) - Kendi Hesabınıza",
    "Crunchyroll Ortak Hesap (1 Aylk)": "Crunchyroll (1 Aylık Ortak Hesap)",
    "Crunchyroll zel Profil (1 Aylk)": "Crunchyroll (1 Aylık Özel Profil)",
    "Magnific AI Ortak (1 Aylk Business Hesap)": "Magnific AI (1 Aylık Business Ortak)",
    "Magnific AI Ortak (1 Aylk Business)": "Magnific AI (1 Aylık Business Ortak)",
    "Scribd (1 Aylk) - Ortak Hesap": "Scribd (1 Aylık) - Ortak Hesap",
    "Scribd (1 Aylk) - Kiisel Hesap": "Scribd (1 Aylık) - Kişisel Hesap",
    "DeepL AI (1 Aylk) - Ortak Hesap": "DeepL AI (1 Aylık) - Ortak Hesap",
    "DeepL AI (1 Aylk) - Kiisel Hesap": "DeepL AI (1 Aylık) - Kişisel Hesap",
    "Perplexity Pro (1 Aylk Hesap)": "Perplexity Pro (1 Aylık Hesap)",
    "Eski Tarihli Telegram Hesab (+1 No'lu)": "Eski Tarihli Telegram Hesabı (+1 No'lu)",
    "Semrush Pro (14 Gnlk Hesap)": "Semrush Pro (14 Günlük Hesap)",
    "Shell 75 TL Akaryakt Puan": "Shell 75 TL Akaryakıt Puanı",
    "Instagram 1000 Takipi (30 Gn Telafili & Dmeyen)": "Instagram 1.000 Takipçi (30 Gün Telafili & Düşmeyen)",
    "Gamma Pro (1 Aylk Hesap)": "Gamma Pro (1 Aylık Hesap)",
    "Gamma Ultra (1 Aylk Hesap)": "Gamma Ultra (1 Aylık Hesap)",
    "Super Grok (12 Aylk Hesap)": "Super Grok (12 Aylık Hesap)",
    "Super Grok (6 Aylk Hesap)": "Super Grok (6 Aylık Hesap)",
    "Super Grok (3 Aylk Hesap)": "Super Grok (3 Aylık Hesap)",
    "Super Grok (1 Aylk Hesap)": "Super Grok (1 Aylık Hesap)",
    "Adobe Creative Cloud (1 Aylk) - Ortak Hesap": "Adobe Creative Cloud (1 Aylık Ortak)",
    "Adobe Creative Cloud (1 Haftalk) - Kendi Hesabnza": "Adobe Creative Cloud (1 Haftalık Kişisel)",
    "Envato Elements (1 Aylk Kiisel)": "Envato Elements (1 Aylık Kişisel)",
    "Freepik Premium (1 Aylk Kiisel)": "Freepik Premium (1 Aylık Kişisel)",
    "Adobe Creative Cloud (1 Aylk Bireysel)": "Adobe Creative Cloud (1 Aylık Bireysel)",
    "Office 365 Pro Plus Kiisel Hesap": "Office 365 Pro Plus Kişisel Hesap",
    "Gmail Hesap (3 Gn Garantili)": "Gmail Hesap (3 Gün Garantili)",
}

def clean_text(text):
    if not text:
        return text
    if text in TITLE_FIXES:
        return TITLE_FIXES[text]
    
    # Generic replacement
    t = text
    t = t.replace("retmen", "Öğretmen")
    t = t.replace("renci", "Öğrenci")
    t = t.replace("zel", "Özel")
    t = t.replace("stediiniz", "İstediğiniz")
    t = t.replace("yelik", "Üyelik")
    t = t.replace("Kiisel", "Kişisel")
    t = t.replace("Deitirilebilir", "Değiştirilebilir")
    t = t.replace("Deien", "Değişen")
    t = t.replace("Deerinde", "Değerinde")
    t = t.replace("Aylk", "Aylık")
    t = t.replace("Yllk", "Yıllık")
    t = t.replace("Yl", "Yıl")
    t = t.replace("Gn", "Gün")
    t = t.replace("Gnlk", "Günlük")
    t = t.replace("Hesabna", "Hesabına")
    t = t.replace("Hesabnza", "Hesabınıza")
    t = t.replace("Hesab", "Hesabı")
    t = t.replace("Snf", "Sınıf")
    t = t.replace("Snrsz", "Sınırsız")
    t = t.replace("Takviye", "Takviye")
    t = t.replace("Anahtar", "Anahtarı")
    t = t.replace("Reklamsz", "Reklamsız")
    t = t.replace("Balants", "Bağlantısı")
    t = t.replace("Akaryakt", "Akaryakıt")
    t = t.replace("Puan", "Puanı")
    t = t.replace("Takipi", "Takipçi")
    t = t.replace("Dmeyen", "Düşmeyen")
    t = t.replace("Magnific", "Magnific")
    return t

# Clean KeyVadi
with open('miniapp/products_db.json', 'r', encoding='utf-8') as f:
    kv = json.load(f)

for p in kv:
    p['title'] = clean_text(p.get('title', ''))
    if 'description' in p and p['description']:
        p['description'] = clean_text(p['description'])
    if 'delivery_label' in p and p['delivery_label']:
        p['delivery_label'] = clean_text(p['delivery_label'])

with open('miniapp/products_db.json', 'w', encoding='utf-8') as f:
    json.dump(kv, f, ensure_ascii=False, indent=2)

# Clean LisansArena
with open('miniapp_lisansarena/products_db.json', 'r', encoding='utf-8') as f:
    la = json.load(f)

for p in la:
    p['title'] = clean_text(p.get('title', ''))
    if 'description' in p and p['description']:
        p['description'] = clean_text(p['description'])
    if 'desc' in p and p['desc']:
        p['desc'] = clean_text(p['desc'])
    if 'delivery' in p and p['delivery']:
        p['delivery'] = clean_text(p['delivery'])

with open('miniapp_lisansarena/products_db.json', 'w', encoding='utf-8') as f:
    json.dump(la, f, ensure_ascii=False, indent=2)

print("SUCCESS: Repaired all Turkish titles and descriptions in both databases!")
