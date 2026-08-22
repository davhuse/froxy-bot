# -*- coding: utf-8 -*-
import json
import os
import shutil
from pathlib import Path

BASE_DIR = Path('.')
KV_PRODUCTS_DIR = BASE_DIR / 'miniapp' / 'assets' / 'products'
KV_PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)
LA_PRODUCTS_DIR = BASE_DIR / 'miniapp_lisansarena' / 'assets' / 'products'

# 1. Copy all clean cards from LisansArena to KeyVadi
for item in LA_PRODUCTS_DIR.glob('card_clean_*.jpg'):
    dest = KV_PRODUCTS_DIR / item.name
    shutil.copy2(item, dest)
    print(f"Copied {item.name} -> {dest}")

# 2. Copy extra brain cards
BRAIN_DIR = Path(r"C:\Users\habil\.gemini\antigravity\brain")

extras = {
    "card_clean_chatgpt.jpg": BRAIN_DIR / "b3d6b142-698f-408f-8efb-52bc1b303e13" / "chatgpt_plus_3d_1787169397228.jpg",
    "card_clean_xbox.jpg": BRAIN_DIR / "b3d6b142-698f-408f-8efb-52bc1b303e13" / "xbox_gamepass_listing_1787169507818.jpg",
    "card_clean_discord.jpg": BRAIN_DIR / "ed3941df-49b3-4746-98df-0ef5ef475eb2" / "discord_14x_boost_banner_1785189209252.jpg",
    "card_clean_kaspersky.jpg": BRAIN_DIR / "ed3941df-49b3-4746-98df-0ef5ef475eb2" / "kaspersky_premium_1y_banner_1785189498076.jpg",
}

for name, src in extras.items():
    if src.exists():
        dest = KV_PRODUCTS_DIR / name
        shutil.copy2(src, dest)
        print(f"Copied extra {name} -> {dest}")
    else:
        print(f"Extra source not found: {src}")

# 3. Product mapping keywords to clean cards
CARD_MAP = [
    ("youtube", "assets/products/card_clean_youtube.jpg"),
    ("canva", "assets/products/card_clean_canva.jpg"),
    ("netflix", "assets/products/card_clean_netflix.jpg"),
    ("chatgpt", "assets/products/card_clean_chatgpt.jpg"),
    ("gpt", "assets/products/card_clean_chatgpt.jpg"),
    ("gemini", "assets/products/card_clean_gemini.jpg"),
    ("spotify", "assets/products/card_clean_spotify.jpg"),
    ("fc 26", "assets/products/card_clean_fc26.jpg"),
    ("fc26", "assets/products/card_clean_fc26.jpg"),
    ("steam", "assets/products/card_clean_steam.jpg"),
    ("capcut", "assets/products/card_clean_capcut.jpg"),
    ("xbox", "assets/products/card_clean_xbox.jpg"),
    ("game pass", "assets/products/card_clean_xbox.jpg"),
    ("gamepass", "assets/products/card_clean_xbox.jpg"),
    ("duolingo", "assets/products/card_clean_duolingo.jpg"),
    ("discord", "assets/products/card_clean_discord.jpg"),
    ("nitro", "assets/products/card_clean_discord.jpg"),
    ("kaspersky", "assets/products/card_clean_kaspersky.jpg"),
    ("windows", "assets/products/card_clean_windows.jpg"),
    ("win 11", "assets/products/card_clean_windows.jpg"),
    ("win 10", "assets/products/card_clean_windows.jpg"),
    ("office", "assets/products/card_clean_office.jpg"),
    ("365", "assets/products/card_clean_office.jpg"),
    ("exxen", "assets/products/card_clean_exxen.jpg"),
    ("prime", "assets/products/card_clean_prime.jpg"),
    ("hbo", "assets/products/card_clean_hbo.jpg"),
    ("roblox", "assets/products/card_clean_roblox.jpg"),
    ("minecraft", "assets/products/card_clean_minecraft.jpg"),
    ("cape", "assets/products/card_clean_minecraft.jpg"),
    ("envato", "assets/products/card_clean_envato.jpg"),
    ("freepik", "assets/products/card_clean_freepik.jpg"),
    ("adobe", "assets/products/card_clean_adobe.jpg"),
    ("creative cloud", "assets/products/card_clean_adobe.jpg"),
    ("photoshop", "assets/products/card_clean_adobe.jpg"),
    ("zula", "assets/products/card_clean_zula.jpg"),
    ("grammarly", "assets/products/card_clean_grammarly.jpg"),
    ("deepl", "assets/products/card_clean_deepl.jpg"),
    ("gamma", "assets/products/card_clean_gamma.jpg"),
    ("magnific", "assets/products/card_clean_magnific.jpg"),
    ("perplexity", "assets/products/card_clean_perplexity.jpg"),
    ("grok", "assets/products/card_clean_grok.jpg"),
    ("scribd", "assets/products/card_clean_scribd.jpg"),
    ("shell", "assets/products/card_clean_shell.jpg"),
    ("telegram", "assets/products/card_clean_telegram.jpg"),
    ("crunchyroll", "assets/products/card_clean_crunchyroll.jpg"),
    ("gmail", "assets/products/card_clean_gmail.jpg"),
    ("instagram", "assets/products/card_clean_instagram.jpg"),
    ("takipci", "assets/products/card_clean_instagram.jpg")
]

def get_clean_card(title):
    t = title.lower()
    for kw, img in CARD_MAP:
        if kw in t:
            return img
    return "assets/products/card_clean_canva.jpg"

def clean_turkish(text):
    if not text:
        return ""
    replacements = {
        "Aylk": "Aylık", "Aylik": "Aylık", "aylk": "aylık", "aylik": "aylık",
        "Kiisel": "Kişisel", "Kisisel": "Kişisel", "kiisel": "kişisel",
        "zel": "Özel", "Ozel": "Özel", "retmen": "Öğretmen",
        "Deiebilir": "Değişebilir", "Deitirilebilir": "Değiştirilebilir",
        "Deien": "Değişen", "Balants": "Bağlantısı", "Balantisi": "Bağlantısı",
        "Gn": "Gün", "gn": "gün", "Yllk": "Yıllık", "yllk": "yıllık",
        "ndirim": "İndirim", "letiim": "İletişim", "ye": "Üye",
        "rn": "Ürün", "Hesab": "Hesabı", "Paketi": "Paketi",
        "Profil": "Profil", "Sresi": "Süresi", "cret": "Ücret"
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

with open('miniapp/products_db.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# Update each product
for p in products:
    p['title'] = clean_turkish(p.get('title', ''))
    p['description'] = clean_turkish(p.get('description', ''))
    p['image'] = get_clean_card(p['title'])

# Vitrin sorting priority
VITRIN_KEYWORDS = [
    "youtube", "canva", "netflix", "chatgpt", "gemini", "spotify",
    "fc 26", "fc26", "steam", "capcut", "xbox", "game pass",
    "duolingo", "discord", "windows", "office", "exxen", "kaspersky"
]

def vitrin_priority(p):
    t = p.get('title', '').lower()
    for idx, kw in enumerate(VITRIN_KEYWORDS):
        if kw in t:
            return idx
    return 999

# Mark top products as showcase/vitrin
for p in products:
    p['is_vitrin'] = (vitrin_priority(p) < 999)
    p['showcase'] = p['is_vitrin']

products.sort(key=vitrin_priority)

with open('miniapp/products_db.json', 'w', encoding='utf-8') as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print(f"KeyVadi products_db.json updated with {len(products)} products and clean 3D cards!")
