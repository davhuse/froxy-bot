#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LisansArena — Neo-Arena Titanium & Emerald CyberVault (v7.0)
KeyVadi'den %100 farklı: Titanyum Metalik, Zümrüt Neon ve Fütüristik Kasa Tasarımı.
Tüm 34 ürün için yüksek çözünürlüklü 1200x1200px kapaklar üretir.
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
FONT_REGULAR = "C:/Windows/Fonts/segoeui.ttf"

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

THEMES_V7 = {
    "canva": {
        "bg_top": (10, 24, 20), "bg_bot": (4, 10, 8),
        "primary": (0, 255, 136), "accent": (94, 234, 212), "border": (16, 185, 129),
        "label": "CANVA PRO DESIGNER", "sub": "SINIRSIZ ŞABLON • 1 YILLIK YETKİ"
    },
    "gemini": {
        "bg_top": (12, 16, 32), "bg_bot": (5, 7, 16),
        "primary": (99, 102, 241), "accent": (165, 180, 252), "border": (79, 70, 229),
        "label": "GOOGLE GEMINI ADVANCED", "sub": "1.5 PRO / ULTRA • 2TB CLOUD"
    },
    "grok": {
        "bg_top": (28, 14, 8), "bg_bot": (12, 5, 2),
        "primary": (249, 115, 22), "accent": (253, 186, 116), "border": (234, 88, 12),
        "label": "xAI SUPER GROK", "sub": "GROK-3 • REASONING AI"
    },
    "fc26": {
        "bg_top": (20, 22, 10), "bg_bot": (8, 9, 3),
        "primary": (234, 179, 8), "accent": (253, 224, 71), "border": (202, 138, 4),
        "label": "EA SPORTS FC26 ONLINE", "sub": "ULTIMATE TEAM • FULL ERİŞİM"
    },
    "steam": {
        "bg_top": (8, 20, 32), "bg_bot": (3, 8, 15),
        "primary": (14, 165, 233), "accent": (125, 211, 252), "border": (2, 132, 199),
        "label": "STEAM STORE VIP", "sub": "GLOBAL RANDOM KEY • ANINDA TESLİM"
    },
    "telegram": {
        "bg_top": (6, 18, 30), "bg_bot": (2, 7, 14),
        "primary": (6, 182, 212), "accent": (103, 232, 249), "border": (8, 145, 178),
        "label": "TELEGRAM ONAYLI HESAP", "sub": "+1 ABD NUMARALI • KURULU OTURUM"
    },
    "windows": {
        "bg_top": (10, 18, 36), "bg_bot": (4, 8, 18),
        "primary": (59, 130, 246), "accent": (147, 197, 253), "border": (37, 99, 235),
        "label": "WINDOWS 10/11 PRO", "sub": "ORİJİNAL RETAIL KEY • ÖMÜR BOYU"
    },
    "office": {
        "bg_top": (26, 10, 10), "bg_bot": (10, 4, 4),
        "primary": (239, 68, 68), "accent": (252, 165, 165), "border": (220, 38, 38),
        "label": "MICROSOFT OFFICE 365", "sub": "WORD • EXCEL • 1 YILLIK LİSANS"
    },
    "zula": {
        "bg_top": (24, 18, 6), "bg_bot": (10, 7, 2),
        "primary": (245, 158, 11), "accent": (253, 230, 138), "border": (217, 119, 6),
        "label": "ZULA RANDOM HESAP", "sub": "1000-3000 ALTIN • 1-155 LEVEL"
    },
    "default": {
        "bg_top": (10, 16, 26), "bg_bot": (4, 7, 12),
        "primary": (0, 255, 136), "accent": (148, 163, 184), "border": (16, 185, 129),
        "label": "LISANSARENA CYBERVAULT", "sub": "7/24 OTOMATİK AKTİVASYON"
    }
}

def detect_v7_theme(title):
    t = title.lower()
    for k in THEMES_V7:
        if k != "default" and k in t:
            return THEMES_V7[k]
    return THEMES_V7["default"]

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
    return "ORİJİNAL LİSANS"

def create_v7_cover(product, output_path):
    W, H = 1200, 1200
    img = Image.new("RGB", (W, H), (6, 9, 15))
    draw = ImageDraw.Draw(img)

    title = product.get("title", "LisansArena Ürün")
    price = product.get("price", "₺49.90")
    theme = detect_v7_theme(title)
    variant = extract_variant(title)

    # 1. Background: Dark Titanium Slate Gradient
    bg_top, bg_bot = theme["bg_top"], theme["bg_bot"]
    primary, accent, border = theme["primary"], theme["accent"], theme["border"]

    for y in range(H):
        ratio = y / H
        smooth = ratio * ratio * (3 - 2 * ratio)
        r = int(bg_top[0] * (1 - smooth) + bg_bot[0] * smooth)
        g = int(bg_top[1] * (1 - smooth) + bg_bot[1] * smooth)
        b = int(bg_top[2] * (1 - smooth) + bg_bot[2] * smooth)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # High-Tech Grid Dots
    for gx in range(60, W - 60, 40):
        for gy in range(60, H - 60, 40):
            draw.point((gx, gy), fill=(255, 255, 255, 18))

    # Titanium Armor Outer Hex Frame
    draw.rectangle([24, 24, W-24, H-24], outline=border, width=2)
    draw.rectangle([34, 34, W-34, H-34], outline=(255, 255, 255, 20), width=1)

    # Corner Neon Notch Elements
    notch = 45
    for cx, cy in [(24, 24), (W-24, 24), (24, H-24), (W-24, H-24)]:
        dx = 1 if cx == 24 else -1
        dy = 1 if cy == 24 else -1
        draw.line([(cx, cy), (cx + dx * notch, cy)], fill=primary, width=6)
        draw.line([(cx, cy), (cx, cy + dy * notch)], fill=primary, width=6)

    # 2. Header: Floating Capsule Badge
    f_badge = get_font(FONT_BOLD, 22)
    
    # Left: LisansArena CyberVault
    draw_rounded_rect(draw, [60, 50, 450, 105], radius=14, fill=(11, 15, 25), outline=primary, width=2)
    draw.text((80, 64), "🛡️ LISANSARENA VAULT", font=f_badge, fill=primary)

    # Right: Instant Delivery
    draw_rounded_rect(draw, [W-390, 50, W-60, 105], radius=14, fill=(11, 15, 25), outline=(0, 255, 136), width=2)
    draw.text((W-365, 64), "⚡ OTOMATİK TESLİM", font=f_badge, fill=(0, 255, 136))

    # 3. Product Headline
    f_title = get_font(FONT_TITLE, 46 if len(title) > 30 else 52)
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
        y_pos = start_y + idx * 62
        draw.text((63, y_pos + 3), line, font=f_title, fill=(0, 0, 0))
        draw.text((60, y_pos), line, font=f_title, fill=(255, 255, 255))

    # 4. Variation Ribbon
    var_y = start_y + len(lines[:2]) * 62 + 20
    f_var = get_font(FONT_BOLD, 30)
    var_label = f"◆  {variant}  ◆"
    v_bbox = draw.textbbox((0, 0), var_label, font=f_var)
    v_w = v_bbox[2] - v_bbox[0] + 50
    draw_rounded_rect(draw, [60, var_y, 60 + v_w, var_y + 60], radius=12, fill=border, outline=primary, width=2)
    draw.text((85, var_y + 11), var_label, font=f_var, fill=(255, 255, 255))

    # 5. Center Cyber Armor Plaque
    card_y = var_y + 85
    card_h = 370
    draw_rounded_rect(draw, [60, card_y, W-60, card_y + card_h], radius=24, fill=(11, 15, 25), outline=border, width=2)
    draw_rounded_rect(draw, [70, card_y + 10, W-70, card_y + card_h - 10], radius=18, fill=(15, 21, 35), outline=(255, 255, 255, 15), width=1)

    # Top Brand Header inside card
    draw_rounded_rect(draw, [95, card_y + 35, 175, card_y + 115], radius=14, fill=(8, 12, 20), outline=primary, width=2)
    draw.text((112, card_y + 48), "LA", font=get_font(FONT_TITLE, 46), fill=primary)

    draw.text((195, card_y + 42), theme["label"], font=get_font(FONT_TITLE, 38), fill=(255, 255, 255))
    draw.text((195, card_y + 92), theme["sub"], font=get_font(FONT_BOLD, 21), fill=accent)

    # 3 Check Features
    features = [
        "✔ %100 Orijinal & Güvenli Teslimat Garantisi",
        "✔ Süre Boyunca Birebir Telafi ve Değişim Güvencesi",
        "✔ 7/24 Canlı Telegram & WhatsApp Destek (@LisansArena)"
    ]
    f_feat = get_font(FONT_BOLD, 25)
    for idx, feat in enumerate(features):
        fy = card_y + 175 + idx * 52
        draw.text((95, fy), feat, font=f_feat, fill=(226, 232, 240))

    # 6. Bottom Banner: Guarantee Box (Left) + Emerald Price Tag (Right)
    bot_y = card_y + card_h + 35

    # Guarantee Shield
    draw_rounded_rect(draw, [60, bot_y, 470, bot_y + 115], radius=20, fill=(11, 15, 25), outline=(0, 255, 136), width=2)
    draw.text((85, bot_y + 20), "🛡️ %100 GARANTİLİ", font=get_font(FONT_BOLD, 28), fill=(0, 255, 136))
    draw.text((85, bot_y + 66), "LISANSARENA RESMİ GÜVENCE", font=get_font(FONT_BOLD, 17), fill=(148, 163, 184))

    # Price Tag
    draw_rounded_rect(draw, [W-470, bot_y, W-60, bot_y + 115], radius=20, fill=(11, 15, 25), outline=primary, width=2)
    draw.text((W-440, bot_y + 16), "FIRSAT FİYATI", font=get_font(FONT_BOLD, 20), fill=accent)
    draw.text((W-440, bot_y + 46), price, font=get_font(FONT_TITLE, 48), fill=(255, 255, 255))

    img.save(output_path, "JPEG", quality=95)
    return output_path

if __name__ == "__main__":
    links_path = BASE_DIR / "lisansarena_shopier_links.json"
    with open(links_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    print(f"[*] LisansArena v7.0 Neo-Titanium {len(raw_items)} adet kapak üretiliyor...")
    seen = set()
    la_products = []
    
    for item in raw_items:
        pid = str(item["id"])
        if pid in seen:
            continue
        seen.add(pid)
        
        out_name = f"la_v7_{pid}.jpg"
        out_path = LA_OUTPUT_DIR / out_name
        create_v7_cover(item, str(out_path))

        title = item["title"]
        price = item["price"]
        clean_p = price.replace("TL", "").replace("₺", "").strip().replace(".", "").replace(",", ".")
        try:
            p_num = float(clean_p)
        except Exception:
            p_num = 0.0

        t_low = title.lower()
        if any(k in t_low for k in ["fc26", "zula", "steam"]):
            cat = "gaming"
        elif any(k in t_low for k in ["gemini", "grok", "chatgpt", "perplexity", "deepl", "gamma", "magnific"]):
            cat = "ai"
        elif any(k in t_low for k in ["canva", "adobe", "capcut"]):
            cat = "design"
        elif any(k in t_low for k in ["windows", "office", "kaspersky"]):
            cat = "software"
        elif any(k in t_low for k in ["telegram", "discord"]):
            cat = "social"
        elif any(k in t_low for k in ["crunchyroll", "netflix", "hbo", "prime", "exxen"]):
            cat = "cinema"
        elif any(k in t_low for k in ["shell", "trendyol", "kupon"]):
            cat = "coupons"
        else:
            cat = "ai"

        is_showcase = any(k in t_low for k in ["canva", "fc26", "gemini", "grok", "telegram", "windows", "office", "steam", "zula", "perplexity"])

        prod = {
            "id": pid,
            "title": title,
            "price": price,
            "price_num": p_num,
            "category": cat,
            "image": f"assets/products/{out_name}",
            "badge": "💎 Arena VIP" if is_showcase else "⚡ Orijinal",
            "url": item.get("url", f"https://www.shopier.com/lisansarena/{pid}"),
            "description": item.get("description", f"{title} - LisansArena güvencesiyle 7/24 anında teslimat ve telafi desteği."),
            "showcase": is_showcase,
            "is_vitrin": is_showcase
        }
        la_products.append(prod)
        print(f"[+] LisansArena v7.0: {title} -> {out_name}")

    out_db = LA_MINIAPP_DIR / "products_db.json"
    with open(out_db, "w", encoding="utf-8") as f:
        json.dump(la_products, f, ensure_ascii=False, indent=2)

    print(f"\n[✓] LisansArena v7.0 Neo-Titanium {len(la_products)} kapak ve veritabanı başarıyla üretildi!")
