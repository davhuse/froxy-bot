#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeyVadi — Ultra-Premium E-Ticaret & Mini App İlan Kapağı Motoru (v6.0)
Tüm 61 ürünün varyasyonunu (1 Aylık, 3 Aylık, 1 Yıllık, 1 Haftalık, Ortak, Kişisel, +1 No vb.)
birebir doğru başlık, varyasyon rozeti, altın garanti mührü ve fiyat etiketi ile üretir.
Vitrin İlanları (Showcase) etiketlerini products_db.json'a otomatik işler.
"""

import os
import sys
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_DB_PATH = BASE_DIR / "miniapp" / "products_db.json"
OUTPUT_DIR = BASE_DIR / "miniapp" / "assets" / "products"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Font configurations (Segoe UI Bold & Arial Bold natively support full Turkish UTF-8)
FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
FONT_REGULAR = "C:/Windows/Fonts/segoeui.ttf"
FONT_TITLE = "C:/Windows/Fonts/arialbd.ttf"

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

# Rich color palettes per brand
THEMES = {
    "netflix": {
        "bg_top": (35, 0, 5), "bg_bot": (10, 0, 2),
        "accent": (229, 9, 20), "glow": (255, 60, 80), "border": (255, 30, 40),
        "brand_name": "NETFLIX 4K ULTRA HD", "tag": "4K UHD • TÜRKÇE DUBLAJ"
    },
    "chatgpt": {
        "bg_top": (0, 35, 28), "bg_bot": (0, 10, 8),
        "accent": (16, 163, 127), "glow": (0, 240, 180), "border": (0, 200, 150),
        "brand_name": "OPENAI CHATGPT PLUS", "tag": "GPT-4o • DALL-E 3 • SINIRSIZ"
    },
    "gemini": {
        "bg_top": (5, 25, 60), "bg_bot": (2, 8, 20),
        "accent": (66, 133, 244), "glow": (120, 190, 255), "border": (50, 140, 255),
        "brand_name": "GOOGLE GEMINI ADVANCED", "tag": "1.5 PRO / ULTRA • 2TB DRIVE"
    },
    "grok": {
        "bg_top": (45, 18, 0), "bg_bot": (15, 5, 0),
        "accent": (255, 102, 0), "glow": (255, 170, 50), "border": (255, 120, 0),
        "brand_name": "xAI SUPER GROK", "tag": "ELON MUSK AI • REASONING"
    },
    "canva": {
        "bg_top": (10, 30, 55), "bg_bot": (15, 5, 35),
        "accent": (0, 196, 204), "glow": (160, 60, 255), "border": (0, 210, 220),
        "brand_name": "CANVA PRO DESIGNER", "tag": "100M+ ŞABLON • ARKA PLAN SİLİCİ"
    },
    "spotify": {
        "bg_top": (0, 40, 18), "bg_bot": (0, 12, 5),
        "accent": (30, 215, 96), "glow": (60, 255, 140), "border": (40, 230, 110),
        "brand_name": "SPOTIFY PREMIUM", "tag": "REKLAMSIZ • ÇEVRİMDIŞI İNDİRME"
    },
    "youtube": {
        "bg_top": (40, 5, 5), "bg_bot": (12, 0, 0),
        "accent": (255, 0, 0), "glow": (255, 90, 90), "border": (255, 40, 40),
        "brand_name": "YOUTUBE PREMIUM", "tag": "REKLAMSIZ • YT MUSIC DAHİL"
    },
    "xbox": {
        "bg_top": (5, 40, 12), "bg_bot": (0, 12, 2),
        "accent": (16, 124, 16), "glow": (60, 230, 60), "border": (30, 200, 30),
        "brand_name": "XBOX GAME PASS ULTIMATE", "tag": "400+ OYUN • PC & KONSOL & CLOUD"
    },
    "steam": {
        "bg_top": (15, 30, 50), "bg_bot": (5, 10, 20),
        "accent": (102, 192, 244), "glow": (240, 190, 80), "border": (80, 180, 240),
        "brand_name": "STEAM STORE VIP", "tag": "GLOBAL KEY • ANINDA TESLİMAT"
    },
    "discord": {
        "bg_top": (25, 25, 60), "bg_bot": (8, 8, 22),
        "accent": (88, 101, 242), "glow": (150, 165, 255), "border": (110, 125, 255),
        "brand_name": "DISCORD NITRO BOOST", "tag": "14X SUNUCU TAKVİYESİ • HD YAYIN"
    },
    "telegram": {
        "bg_top": (10, 30, 60), "bg_bot": (5, 12, 25),
        "accent": (36, 161, 222), "glow": (90, 210, 255), "border": (50, 180, 240),
        "brand_name": "TELEGRAM VIP HESAP", "tag": "+1 ABD ONAYLI • SPAMSIZ OTURUM"
    },
    "hbo": {
        "bg_top": (30, 10, 55), "bg_bot": (10, 2, 20),
        "accent": (153, 51, 204), "glow": (210, 110, 255), "border": (170, 70, 220),
        "brand_name": "HBO MAX 4K ULTRA HD", "tag": "4K HDR • WARNER BROS • DC UNIVERSE"
    },
    "crunchyroll": {
        "bg_top": (45, 25, 5), "bg_bot": (15, 5, 0),
        "accent": (244, 117, 33), "glow": (255, 170, 70), "border": (255, 130, 40),
        "brand_name": "CRUNCHYROLL PREMIUM", "tag": "MEGA FAN • EŞ ZAMANLI YAYINLAR"
    },
    "prime": {
        "bg_top": (5, 25, 50), "bg_bot": (0, 8, 18),
        "accent": (0, 168, 225), "glow": (80, 210, 255), "border": (20, 180, 240),
        "brand_name": "AMAZON PRIME VIDEO", "tag": "PRIME ORIGINALS • 4K ULTRA HD"
    },
    "disney": {
        "bg_top": (5, 20, 55), "bg_bot": (2, 5, 20),
        "accent": (17, 60, 207), "glow": (80, 150, 255), "border": (40, 100, 230),
        "brand_name": "DISNEY+ REKLAMSIZ UHD", "tag": "MARVEL • STAR WARS • PIXAR • 4K"
    },
    "capcut": {
        "bg_top": (0, 35, 40), "bg_bot": (0, 10, 15),
        "accent": (0, 229, 255), "glow": (0, 255, 220), "border": (0, 240, 255),
        "brand_name": "CAPCUT PRO VIP", "tag": "4K 60FPS DIŞA AKTARIM • TÜM PRO EFEKTLER"
    },
    "adobe": {
        "bg_top": (40, 5, 12), "bg_bot": (15, 0, 2),
        "accent": (255, 0, 0), "glow": (255, 110, 110), "border": (255, 50, 50),
        "brand_name": "ADOBE CREATIVE CLOUD", "tag": "PHOTOSHOP • PREMIERE • AFTER EFFECTS"
    },
    "kaspersky": {
        "bg_top": (0, 40, 35), "bg_bot": (0, 12, 10),
        "accent": (0, 168, 142), "glow": (0, 240, 200), "border": (0, 200, 170),
        "brand_name": "KASPERSKY PREMIUM", "tag": "SINIRSIZ VPN • GÜVENLİK VE ANTİVİRÜS"
    },
    "fc26": {
        "bg_top": (30, 30, 5), "bg_bot": (10, 10, 0),
        "accent": (230, 190, 40), "glow": (100, 255, 120), "border": (255, 210, 50),
        "brand_name": "EA SPORTS FC26 + ONLINE", "tag": "ULTIMATE TEAM • HER ŞEYİ DEĞİŞEN HESAP"
    },
    "zula": {
        "bg_top": (40, 30, 5), "bg_bot": (12, 8, 0),
        "accent": (240, 190, 30), "glow": (255, 220, 80), "border": (255, 200, 40),
        "brand_name": "ZULA RANDOM HESAP", "tag": "MIN 1000-3000 ALTIN • 1-155 LEVEL"
    },
    "deepl": {
        "bg_top": (10, 25, 55), "bg_bot": (2, 8, 20),
        "accent": (15, 43, 70), "glow": (20, 150, 255), "border": (30, 110, 230),
        "brand_name": "DEEPL PRO AI TRANSLATE", "tag": "SINIRSIZ ÇEVİRİ • DÖKÜMAN VE METİN"
    },
    "grammarly": {
        "bg_top": (5, 40, 30), "bg_bot": (0, 12, 8),
        "accent": (21, 168, 95), "glow": (60, 240, 150), "border": (40, 200, 120),
        "brand_name": "GRAMMARLY PREMIUM", "tag": "GELİŞMİŞ YAZIM VE GRAMER DÜZELTME"
    },
    "perplexity": {
        "bg_top": (10, 30, 40), "bg_bot": (2, 10, 15),
        "accent": (32, 178, 170), "glow": (80, 230, 220), "border": (50, 200, 190),
        "brand_name": "PERPLEXITY PRO AI", "tag": "CLAUDE 3.5 & GPT-4o • PRO SEARCH"
    },
    "semrush": {
        "bg_top": (45, 20, 5), "bg_bot": (15, 5, 0),
        "accent": (255, 100, 45), "glow": (255, 160, 80), "border": (255, 120, 50),
        "brand_name": "SEMRUSH PRO SEO", "tag": "ANAHTAR KELİME • BACKLINK • RAKİP ANALİZİ"
    },
    "scribd": {
        "bg_top": (5, 30, 35), "bg_bot": (0, 10, 15),
        "accent": (26, 123, 138), "glow": (70, 200, 215), "border": (40, 160, 180),
        "brand_name": "SCRIBD PREMIUM", "tag": "SINIRSIZ E-KİTAP • SESLİ KİTAP & MAKALELER"
    },
    "duolingo": {
        "bg_top": (20, 40, 5), "bg_bot": (5, 15, 0),
        "accent": (88, 204, 2), "glow": (140, 255, 40), "border": (110, 230, 10),
        "brand_name": "DUOLINGO SUPER SINIRSIZ", "tag": "SINIRSIZ CAN • REKLAMSIZ • ÇEVRİMDIŞI"
    },
    "windows": {
        "bg_top": (5, 25, 55), "bg_bot": (2, 8, 20),
        "accent": (0, 120, 215), "glow": (70, 180, 255), "border": (30, 150, 240),
        "brand_name": "WINDOWS 11 PRO LİSANS", "tag": "ORİJİNAL RETAIL KEY • ÖMÜR BOYU"
    },
    "office": {
        "bg_top": (40, 20, 5), "bg_bot": (15, 5, 0),
        "accent": (216, 59, 1), "glow": (255, 120, 60), "border": (240, 80, 20),
        "brand_name": "MICROSOFT OFFICE 365", "tag": "WORD • EXCEL • POWERPOINT • 1TB ONEDRIVE"
    },
    "trendyol": {
        "bg_top": (45, 25, 5), "bg_bot": (15, 5, 0),
        "accent": (242, 122, 26), "glow": (255, 170, 60), "border": (255, 140, 40),
        "brand_name": "TRENDYOL İNDİRİM KUPONU", "tag": "YEMEK & MARKET GEÇERLİ • ANINDA ONAYLI"
    },
    "shell": {
        "bg_top": (40, 20, 0), "bg_bot": (15, 0, 0),
        "accent": (251, 186, 0), "glow": (255, 60, 50), "border": (255, 200, 0),
        "brand_name": "SHELL AKARYAKIT PUANI", "tag": "TÜM SHELL İSTASYONLARINDA GEÇERLİ"
    },
    "exxen": {
        "bg_top": (40, 35, 0), "bg_bot": (15, 10, 0),
        "accent": (255, 230, 0), "glow": (255, 255, 100), "border": (255, 240, 50),
        "brand_name": "EXXEN REKLAMSIZ", "tag": "DİZİLER • PROGRAMLAR • REKLAMSIZ"
    },
    "default": {
        "bg_top": (10, 25, 45), "bg_bot": (5, 10, 18),
        "accent": (0, 210, 255), "glow": (60, 180, 255), "border": (30, 160, 240),
        "brand_name": "KEYVADI VIP LİSANS", "tag": "7/24 OTOMATİK TESLİMAT • GARANTİLİ"
    }
}

def detect_theme(title):
    t = title.lower()
    for k in THEMES:
        if k != "default" and k in t:
            return THEMES[k]
    return THEMES["default"]

def draw_rounded_rect(draw, bbox, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)

def extract_variant(title, badge):
    t = title.strip()
    if "(" in t and ")" in t:
        v = t.split("(")[1].split(")")[0].strip().upper()
        if len(v) < 30:
            return v
    if "-" in t:
        v = t.split("-")[-1].strip().upper()
        if len(v) < 30:
            return v
    if "1 YIL" in t.upper() or "1 YILLIK" in t.upper():
        return "1 YILLIK LİSANS"
    if "4 AYLIK" in t.upper():
        return "4 AYLIK ÖZEL KOD"
    if "3 AYLIK" in t.upper():
        return "3 AYLIK ÜYELİK"
    if "1 AYLIK" in t.upper() or "1 AY" in t.upper() or "30 GÜN" in t.upper():
        return "1 AYLIK KULLANIM"
    if "1 HAFTALIK" in t.upper():
        return "1 HAFTALIK DENEME"
    if "14 GÜNLÜK" in t.upper():
        return "14 GÜNLÜK HESAP"
    if "SINIRSIZ" in t.upper():
        return "SINIRSIZ PAKET"
    return badge.replace("👥", "").replace("✨", "").replace("⭐", "").strip().upper()

def create_product_banner(product, output_path):
    W, H = 1200, 1200
    img = Image.new("RGB", (W, H), (8, 10, 15))
    draw = ImageDraw.Draw(img)

    title = product.get("title", "KeyVadi Ürün")
    price = product.get("price", "₺49.90")
    badge = product.get("badge", "POPÜLER")
    theme = detect_theme(title)
    variant = extract_variant(title, badge)

    # 1. Background Mesh Gradient
    bg_top, bg_bot = theme["bg_top"], theme["bg_bot"]
    accent, glow, border = theme["accent"], theme["glow"], theme["border"]

    for y in range(H):
        ratio = y / H
        smooth_ratio = ratio * ratio * (3 - 2 * ratio)
        r = int(bg_top[0] * (1 - smooth_ratio) + bg_bot[0] * smooth_ratio)
        g = int(bg_top[1] * (1 - smooth_ratio) + bg_bot[1] * smooth_ratio)
        b = int(bg_top[2] * (1 - smooth_ratio) + bg_bot[2] * smooth_ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Glow Radial Orbs
    draw.ellipse([-150, -150, 450, 450], fill=None, outline=glow, width=2)
    draw.ellipse([W-400, H-400, W+150, H+150], fill=None, outline=accent, width=2)

    # High-Tech Cyber Outer Frame
    draw.rectangle([24, 24, W-24, H-24], outline=border, width=2)
    draw.rectangle([32, 32, W-32, H-32], outline=(255, 255, 255, 30), width=1)

    # Outer Corner Brackets
    bracket_len = 60
    corners = [(24, 24), (W-24, 24), (24, H-24), (W-24, H-24)]
    for cx, cy in corners:
        dx = 1 if cx == 24 else -1
        dy = 1 if cy == 24 else -1
        draw.line([(cx, cy), (cx + dx * bracket_len, cy)], fill=(255, 255, 255), width=6)
        draw.line([(cx, cy), (cx, cy + dy * bracket_len)], fill=(255, 255, 255), width=6)

    # 2. Header Badges (Store + Auto Delivery)
    f_badge = get_font(FONT_BOLD, 24)
    # Store Pill
    draw_rounded_rect(draw, [55, 50, 360, 105], radius=16, fill=(12, 16, 26), outline=accent, width=2)
    draw.text((75, 62), "⚡ KEYVADI STORE", font=f_badge, fill=(255, 255, 255))

    # Auto Delivery Pill
    draw_rounded_rect(draw, [W-390, 50, W-55, 105], radius=16, fill=(12, 16, 26), outline=(40, 210, 100), width=2)
    draw.text((W-365, 62), "🚀 ANINDA TESLİMAT", font=f_badge, fill=(100, 255, 160))

    # 3. Main Product Title (Clean word wrapping with full Turkish support)
    f_title = get_font(FONT_TITLE, 46 if len(title) > 30 else 54)

    words = title.split()
    lines = []
    curr = ""
    for w in words:
        test = curr + " " + w if curr else w
        bbox = draw.textbbox((0, 0), test, font=f_title)
        if bbox[2] - bbox[0] < W - 140:
            curr = test
        else:
            lines.append(curr)
            curr = w
    if curr:
        lines.append(curr)

    start_y = 140
    for idx, line in enumerate(lines[:2]):
        y_pos = start_y + idx * 64
        draw.text((64, y_pos + 3), line, font=f_title, fill=(0, 0, 0))
        draw.text((60, y_pos), line, font=f_title, fill=(255, 255, 255))

    # 4. Prominent Variation / Duration Pill
    var_y = start_y + len(lines[:2]) * 64 + 20
    f_var = get_font(FONT_BOLD, 32)
    var_label = f"⭐  {variant}  ⭐"
    v_bbox = draw.textbbox((0, 0), var_label, font=f_var)
    v_w = v_bbox[2] - v_bbox[0] + 50
    draw_rounded_rect(draw, [60, var_y, 60 + v_w, var_y + 64], radius=16, fill=accent, outline=glow, width=3)
    draw.text((85, var_y + 12), var_label, font=f_var, fill=(255, 255, 255))

    # 5. 3D Floating VIP Card / Plaque (Centerpiece)
    card_y = var_y + 90
    card_h = 360
    draw_rounded_rect(draw, [60, card_y, W-60, card_y + card_h], radius=28, fill=(12, 16, 26), outline=border, width=3)
    draw_rounded_rect(draw, [70, card_y + 10, W-70, card_y + card_h - 10], radius=22, fill=(18, 24, 38), outline=(255, 255, 255, 20), width=1)

    # Gold Security Chip on Card
    draw_rounded_rect(draw, [100, card_y + 40, 185, card_y + 110], radius=12, fill=(220, 175, 40), outline=(255, 230, 100), width=2)
    draw.line([(100, card_y + 75), (185, card_y + 75)], fill=(160, 120, 20), width=2)
    draw.line([(142, card_y + 40), (142, card_y + 110)], fill=(160, 120, 20), width=2)

    # Brand Title inside Card
    f_card_brand = get_font(FONT_TITLE, 44)
    draw.text((215, card_y + 45), theme["brand_name"], font=f_card_brand, fill=(255, 255, 255))

    # Brand Tagline
    f_card_sub = get_font(FONT_BOLD, 22)
    draw.text((215, card_y + 105), theme["tag"], font=f_card_sub, fill=glow)

    # Feature List inside Card
    features = [
        "✔ %100 Orijinal & Güvenli Teslimat Garantisi",
        "✔ Süre Boyunca KeyVadi Değişim & Telafi Güvencesi",
        "✔ 7/24 Kesintisiz Canlı Telegram & WhatsApp Destek"
    ]
    f_feat = get_font(FONT_BOLD, 26)
    for idx, feat in enumerate(features):
        fy = card_y + 175 + idx * 50
        draw.text((105, fy), feat, font=f_feat, fill=(230, 240, 255))

    # 6. Bottom Banner: Gold Warranty Seal + Price Tag
    bot_y = card_y + card_h + 35

    # Gold Warranty Seal (Left)
    draw_rounded_rect(draw, [60, bot_y, 450, bot_y + 115], radius=22, fill=(35, 28, 10), outline=(240, 195, 40), width=3)
    draw.text((85, bot_y + 20), "🛡️ %100 GARANTİLİ", font=get_font(FONT_BOLD, 30), fill=(255, 225, 80))
    draw.text((85, bot_y + 68), "GÜVENLİ PAZARYERİ ALIŞVERİŞİ", font=get_font(FONT_BOLD, 19), fill=(225, 205, 150))

    # Price Tag (Right)
    draw_rounded_rect(draw, [W-470, bot_y, W-60, bot_y + 115], radius=22, fill=(10, 42, 22), outline=(40, 220, 110), width=3)
    draw.text((W-440, bot_y + 16), "FIRSAT FİYATI", font=get_font(FONT_BOLD, 20), fill=(140, 255, 175))
    draw.text((W-440, bot_y + 46), price, font=get_font(FONT_TITLE, 48), fill=(255, 255, 255))

    # Save output with high quality
    img.save(output_path, "JPEG", quality=95)
    return output_path

SHOWCASE_KEYWORDS = [
    "netflix", "chat gpt", "chatgpt", "canva", "gemini", "xbox", "fc26",
    "telegram", "steam 200", "capcut", "spotify", "youtube", "trendyol",
    "zula", "disney", "windows"
]

if __name__ == "__main__":
    with open(PRODUCTS_DB_PATH, "r", encoding="utf-8") as f:
        products = json.load(f)

    print(f"[*] Toplam {len(products)} ürün için v6.0 ultra-net varyasyon kapakları üretiliyor...")
    for idx, p in enumerate(products):
        pid = str(p["id"])
        out_name = f"cover_v6_{pid}.jpg"
        out_path = OUTPUT_DIR / out_name
        create_product_banner(p, str(out_path))
        p["image"] = f"assets/products/{out_name}"
        
        # Check showcase (vitrin)
        t_low = p["title"].lower()
        is_showcase = any(k in t_low for k in SHOWCASE_KEYWORDS)
        p["showcase"] = is_showcase
        if is_showcase:
            p["is_vitrin"] = True

        print(f"[{idx+1}/{len(products)}] {p['title']} -> {out_name} (Vitrin: {is_showcase})")

    with open(PRODUCTS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print("[+] TÜM 61 ÜRÜNÜN V6.0 KAPAKLARI VE VİTRİN ETİKETLERİ EKSİKSİZ ÜRETİLDİ!")
