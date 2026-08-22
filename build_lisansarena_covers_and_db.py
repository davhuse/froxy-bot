#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LisansArena — Ürün Veritabanı ve v6.0 Ultra-Net İlan Kapakları Üreticisi
"""

import os
import sys
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
LA_MINIAPP_DIR = BASE_DIR / "miniapp_lisansarena"
LA_OUTPUT_DIR = LA_MINIAPP_DIR / "assets" / "products"
LA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
FONT_TITLE = "C:/Windows/Fonts/arialbd.ttf"

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

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
    "steam": {
        "bg_top": (15, 30, 50), "bg_bot": (5, 10, 20),
        "accent": (102, 192, 244), "glow": (240, 190, 80), "border": (80, 180, 240),
        "brand_name": "STEAM STORE VIP", "tag": "GLOBAL KEY • ANINDA TESLİMAT"
    },
    "fc26": {
        "bg_top": (30, 30, 5), "bg_bot": (10, 10, 0),
        "accent": (230, 190, 40), "glow": (100, 255, 120), "border": (255, 210, 50),
        "brand_name": "EA SPORTS FC26 + ONLINE", "tag": "ULTIMATE TEAM • HER ŞEYİ DEĞİŞEN"
    },
    "zula": {
        "bg_top": (40, 30, 5), "bg_bot": (12, 8, 0),
        "accent": (240, 190, 30), "glow": (255, 220, 80), "border": (255, 200, 40),
        "brand_name": "ZULA RANDOM HESAP", "tag": "MIN 1000-3000 ALTIN • 1-155 LEVEL"
    },
    "telegram": {
        "bg_top": (10, 30, 60), "bg_bot": (5, 12, 25),
        "accent": (36, 161, 222), "glow": (90, 210, 255), "border": (50, 180, 240),
        "brand_name": "TELEGRAM VIP HESAP", "tag": "+1 ABD ONAYLI • SPAMSIZ OTURUM"
    },
    "default": {
        "bg_top": (12, 20, 40), "bg_bot": (5, 8, 18),
        "accent": (0, 200, 255), "glow": (80, 180, 255), "border": (40, 150, 230),
        "brand_name": "LISANSARENA VIP LİSANS", "tag": "7/24 OTOMATİK TESLİMAT • GARANTİLİ"
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

def extract_variant(title):
    t = title.strip()
    if "(" in t and ")" in t:
        v = t.split("(")[1].split(")")[0].strip().upper()
        if len(v) < 30:
            return v
    if "-" in t:
        v = t.split("-")[-1].strip().upper()
        if len(v) < 30:
            return v
    if "12 AYLIK" in t.upper() or "1 YILLIK" in t.upper() or "1 YIL" in t.upper():
        return "1 YILLIK LİSANS"
    if "6 AYLIK" in t.upper():
        return "6 AYLIK ÜYELİK"
    if "3 AYLIK" in t.upper():
        return "3 AYLIK ÜYELİK"
    if "1 AYLIK" in t.upper():
        return "1 AYLIK KULLANIM"
    if "1 HAFTALIK" in t.upper():
        return "1 HAFTALIK DENEME"
    return "VIP LİSANS"

def create_banner(product, output_path):
    W, H = 1200, 1200
    img = Image.new("RGB", (W, H), (8, 10, 15))
    draw = ImageDraw.Draw(img)

    title = product.get("title", "LisansArena Ürün")
    price = product.get("price", "₺49.90")
    theme = detect_theme(title)
    variant = extract_variant(title)

    bg_top, bg_bot = theme["bg_top"], theme["bg_bot"]
    accent, glow, border = theme["accent"], theme["glow"], theme["border"]

    for y in range(H):
        ratio = y / H
        smooth = ratio * ratio * (3 - 2 * ratio)
        r = int(bg_top[0] * (1 - smooth) + bg_bot[0] * smooth)
        g = int(bg_top[1] * (1 - smooth) + bg_bot[1] * smooth)
        b = int(bg_top[2] * (1 - smooth) + bg_bot[2] * smooth)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    draw.ellipse([-120, -120, 400, 400], fill=None, outline=glow, width=2)
    draw.ellipse([W-400, H-400, W+120, H+120], fill=None, outline=accent, width=2)

    # High-Tech Cyber Frame
    draw.rectangle([24, 24, W-24, H-24], outline=border, width=2)
    bracket = 60
    for cx, cy in [(24, 24), (W-24, 24), (24, H-24), (W-24, H-24)]:
        dx = 1 if cx == 24 else -1
        dy = 1 if cy == 24 else -1
        draw.line([(cx, cy), (cx + dx * bracket, cy)], fill=(255, 255, 255), width=6)
        draw.line([(cx, cy), (cx, cy + dy * bracket)], fill=(255, 255, 255), width=6)

    # Top Badges
    f_badge = get_font(FONT_BOLD, 24)
    draw_rounded_rect(draw, [55, 50, 410, 105], radius=16, fill=(12, 16, 26), outline=accent, width=2)
    draw.text((75, 62), "⚡ LISANSARENA STORE", font=f_badge, fill=(255, 255, 255))

    draw_rounded_rect(draw, [W-390, 50, W-55, 105], radius=16, fill=(12, 16, 26), outline=(40, 210, 100), width=2)
    draw.text((W-365, 62), "🚀 ANINDA TESLİMAT", font=f_badge, fill=(100, 255, 160))

    # Main Title
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

    # Prominent Variant Pill
    var_y = start_y + len(lines[:2]) * 64 + 20
    f_var = get_font(FONT_BOLD, 32)
    var_label = f"⭐  {variant}  ⭐"
    v_bbox = draw.textbbox((0, 0), var_label, font=f_var)
    v_w = v_bbox[2] - v_bbox[0] + 50
    draw_rounded_rect(draw, [60, var_y, 60 + v_w, var_y + 64], radius=16, fill=accent, outline=glow, width=3)
    draw.text((85, var_y + 12), var_label, font=f_var, fill=(255, 255, 255))

    # Center Feature Card
    card_y = var_y + 90
    card_h = 360
    draw_rounded_rect(draw, [60, card_y, W-60, card_y + card_h], radius=28, fill=(12, 16, 26), outline=border, width=3)
    draw_rounded_rect(draw, [70, card_y + 10, W-70, card_y + card_h - 10], radius=22, fill=(18, 24, 38), outline=(255, 255, 255, 20), width=1)

    # Gold Chip
    draw_rounded_rect(draw, [100, card_y + 40, 185, card_y + 110], radius=12, fill=(220, 175, 40), outline=(255, 230, 100), width=2)
    draw.line([(100, card_y + 75), (185, card_y + 75)], fill=(160, 120, 20), width=2)
    draw.line([(142, card_y + 40), (142, card_y + 110)], fill=(160, 120, 20), width=2)

    draw.text((215, card_y + 45), theme["brand_name"], font=get_font(FONT_TITLE, 44), fill=(255, 255, 255))
    draw.text((215, card_y + 105), theme["tag"], font=get_font(FONT_BOLD, 22), fill=glow)

    features = [
        "✔ %100 Orijinal & Güvenli Teslimat Garantisi",
        "✔ Süre Boyunca LisansArena Değişim & Telafi Güvencesi",
        "✔ 7/24 Kesintisiz Canlı Telegram Destek (@LisansArena)"
    ]
    f_feat = get_font(FONT_BOLD, 26)
    for idx, feat in enumerate(features):
        fy = card_y + 175 + idx * 50
        draw.text((105, fy), feat, font=f_feat, fill=(230, 240, 255))

    # Bottom Warranty & Price Tag
    bot_y = card_y + card_h + 35
    draw_rounded_rect(draw, [60, bot_y, 450, bot_y + 115], radius=22, fill=(35, 28, 10), outline=(240, 195, 40), width=3)
    draw.text((85, bot_y + 20), "🛡️ %100 GARANTİLİ", font=get_font(FONT_BOLD, 30), fill=(255, 225, 80))
    draw.text((85, bot_y + 68), "LISANSARENA GÜVENCESİ", font=get_font(FONT_BOLD, 19), fill=(225, 205, 150))

    draw_rounded_rect(draw, [W-470, bot_y, W-60, bot_y + 115], radius=22, fill=(10, 42, 22), outline=(40, 220, 110), width=3)
    draw.text((W-440, bot_y + 16), "FIRSAT FİYATI", font=get_font(FONT_BOLD, 20), fill=(140, 255, 175))
    draw.text((W-440, bot_y + 46), price, font=get_font(FONT_TITLE, 48), fill=(255, 255, 255))

    img.save(output_path, "JPEG", quality=95)
    return output_path

def parse_price(price_str):
    clean = price_str.replace("TL", "").replace("₺", "").strip()
    if "." in clean and "," in clean:
        clean = clean.replace(".", "").replace(",", ".")
    elif "," in clean:
        clean = clean.replace(",", ".")
    try:
        return float(clean)
    except Exception:
        return 0.0

def categorize(title):
    t = title.lower()
    if any(k in t for k in ["fc26", "zula", "steam"]):
        return "gaming"
    if any(k in t for k in ["gemini", "grok", "chatgpt", "perplexity", "deepl", "gamma", "magnific"]):
        return "ai"
    if any(k in t for k in ["canva", "adobe", "capcut"]):
        return "design"
    if any(k in t for k in ["windows", "office", "kaspersky"]):
        return "software"
    if any(k in t for k in ["telegram", "discord"]):
        return "social"
    if any(k in t for k in ["crunchyroll", "netflix", "hbo", "prime", "exxen"]):
        return "cinema"
    if any(k in t for k in ["shell", "trendyol", "kupon"]):
        return "coupons"
    return "ai"

SHOWCASE_KEYWORDS = ["canva", "fc26", "gemini", "grok", "telegram", "windows", "office", "steam", "zula", "perplexity"]

if __name__ == "__main__":
    links_path = BASE_DIR / "lisansarena_shopier_links.json"
    with open(links_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    la_products = []
    seen_ids = set()

    for item in raw_items:
        pid = str(item["id"])
        if pid in seen_ids:
            continue
        seen_ids.add(pid)

        title = item["title"]
        price = item["price"]
        price_num = parse_price(price)
        cat = categorize(title)
        out_name = f"la_cover_{pid}.jpg"
        out_path = LA_OUTPUT_DIR / out_name
        create_banner(item, str(out_path))

        is_showcase = any(k in title.lower() for k in SHOWCASE_KEYWORDS)

        prod = {
            "id": pid,
            "title": title,
            "price": price,
            "price_num": price_num,
            "category": cat,
            "image": f"assets/products/{out_name}",
            "badge": "⭐ Popüler" if is_showcase else "⚡ Lisans",
            "url": item.get("url", f"https://www.shopier.com/lisansarena/{pid}"),
            "description": item.get("description", f"{title} - LisansArena güvencesiyle 7/24 otomatik anında teslimat ve garanti desteği."),
            "showcase": is_showcase,
            "is_vitrin": is_showcase
        }
        la_products.append(prod)
        print(f"[+] LisansArena Cover Created: {title} -> {out_name}")

    out_db = LA_MINIAPP_DIR / "products_db.json"
    with open(out_db, "w", encoding="utf-8") as f:
        json.dump(la_products, f, ensure_ascii=False, indent=2)

    print(f"\n[✓] Toplam {len(la_products)} LisansArena ürünü ve kapağı başarıyla oluşturuldu!")
