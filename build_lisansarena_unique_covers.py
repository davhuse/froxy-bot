#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LisansArena — Özel Altın & Zümrüt (Obsidian Gold / Emerald Luxury) İlan Kapakları Motoru (v6.0)
KeyVadi'den tamamen farklı; Altın Varak, Zümrüt Neon ve VIP Arena zırhı temasında 1200x1200px kapaklar üretir.
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

# Unique Luxury Color Palettes for LisansArena
LA_THEMES = {
    "canva": {
        "bg_top": (24, 18, 5), "bg_bot": (8, 6, 2),
        "accent": (245, 158, 11), "glow": (255, 215, 0), "border": (217, 119, 6),
        "tag": "CANVA PRO DESIGNER • 1 YIL LİSANS", "badge": "VIP TASARIM"
    },
    "gemini": {
        "bg_top": (5, 20, 30), "bg_bot": (2, 8, 12),
        "accent": (16, 185, 129), "glow": (0, 245, 160), "border": (5, 150, 105),
        "tag": "GOOGLE GEMINI PRO • 2TB CLOUD", "badge": "YAPAY ZEKA"
    },
    "grok": {
        "bg_top": (35, 12, 5), "bg_bot": (12, 4, 2),
        "accent": (234, 88, 12), "glow": (251, 146, 60), "border": (194, 65, 12),
        "tag": "xAI SUPER GROK • REASONING AI", "badge": "ELON MUSK AI"
    },
    "fc26": {
        "bg_top": (28, 24, 5), "bg_bot": (10, 8, 2),
        "accent": (234, 179, 8), "glow": (253, 224, 71), "border": (202, 138, 4),
        "tag": "EA SPORTS FC26 + ONLINE HER ŞEYİ DEĞİŞEN", "badge": "E-SPOR OYUN"
    },
    "steam": {
        "bg_top": (10, 20, 35), "bg_bot": (4, 8, 15),
        "accent": (56, 189, 248), "glow": (186, 230, 253), "border": (14, 165, 233),
        "tag": "STEAM STORE RANDOM KEY • ANINDA TESLİMAT", "badge": "ORİJİNAL KEY"
    },
    "telegram": {
        "bg_top": (5, 22, 35), "bg_bot": (2, 8, 15),
        "accent": (14, 165, 233), "glow": (56, 189, 248), "border": (2, 132, 199),
        "tag": "+1 ABD ONAYLI KURULU ESKİ TARİHLİ HESAP", "badge": "ONAYLI HESAP"
    },
    "zula": {
        "bg_top": (30, 20, 5), "bg_bot": (10, 6, 2),
        "accent": (245, 158, 11), "glow": (252, 211, 77), "border": (217, 119, 6),
        "tag": "ZULA RANDOM HESAP • MIN 1000-3000 ALTIN", "badge": "ANINDA HESAP"
    },
    "windows": {
        "bg_top": (8, 24, 40), "bg_bot": (2, 8, 16),
        "accent": (59, 130, 246), "glow": (147, 197, 253), "border": (37, 99, 235),
        "tag": "WINDOWS 10/11 PRO ORİJİNAL RETAIL KEY", "badge": "ÖMÜR BOYU"
    },
    "office": {
        "bg_top": (35, 15, 5), "bg_bot": (12, 5, 2),
        "accent": (239, 68, 68), "glow": (252, 165, 165), "border": (220, 38, 38),
        "tag": "MICROSOFT OFFICE 365 • 1 YIL LİSANS", "badge": "OFFICE PAKETİ"
    },
    "default": {
        "bg_top": (20, 16, 8), "bg_bot": (6, 5, 3),
        "accent": (217, 119, 6), "glow": (251, 191, 36), "border": (180, 83, 9),
        "tag": "LISANSARENA GÜVENCESİYLE ANINDA TESLİMAT", "badge": "VIP LİSANS"
    }
}

def detect_la_theme(title):
    t = title.lower()
    for k in LA_THEMES:
        if k != "default" and k in t:
            return LA_THEMES[k]
    return LA_THEMES["default"]

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

def create_lisansarena_banner(product, output_path):
    W, H = 1200, 1200
    img = Image.new("RGB", (W, H), (5, 5, 8))
    draw = ImageDraw.Draw(img)

    title = product.get("title", "LisansArena Ürün")
    price = product.get("price", "₺49.90")
    theme = detect_la_theme(title)
    variant = extract_variant(title)

    # 1. Background: Obsidian Luxury Gradient with Gold/Emerald Plasma Flare
    bg_top, bg_bot = theme["bg_top"], theme["bg_bot"]
    accent, glow, border = theme["accent"], theme["glow"], theme["border"]

    for y in range(H):
        ratio = y / H
        smooth = ratio * ratio * (3 - 2 * ratio)
        r = int(bg_top[0] * (1 - smooth) + bg_bot[0] * smooth)
        g = int(bg_top[1] * (1 - smooth) + bg_bot[1] * smooth)
        b = int(bg_top[2] * (1 - smooth) + bg_bot[2] * smooth)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Diagonal Gold Flare lines
    for i in range(-200, W + 400, 120):
        draw.line([(i, 0), (i + 400, H)], fill=(255, 215, 0, 12), width=1)

    # Luxury Gold & Emerald Orbs
    draw.ellipse([-100, -100, 450, 450], fill=None, outline=(245, 158, 11), width=2)
    draw.ellipse([W-420, H-420, W+100, H+100], fill=None, outline=(16, 185, 129), width=2)

    # Gold Octagonal Outer Armor Frame
    draw.rectangle([20, 20, W-20, H-20], outline=(217, 119, 6), width=3)
    draw.rectangle([28, 28, W-28, H-28], outline=(255, 215, 0, 80), width=1)

    # Corner Cut Corner Accents
    c_len = 50
    for cx, cy in [(20, 20), (W-20, 20), (20, H-20), (W-20, H-20)]:
        dx = 1 if cx == 20 else -1
        dy = 1 if cy == 20 else -1
        draw.polygon([
            (cx, cy),
            (cx + dx * c_len, cy),
            (cx, cy + dy * c_len)
        ], fill=(245, 158, 11))

    # 2. Header Brand Shield & Instant Delivery Pill
    f_badge = get_font(FONT_BOLD, 23)
    
    # Left Brand Shield Pill
    draw_rounded_rect(draw, [55, 50, 440, 105], radius=14, fill=(18, 14, 6), outline=(245, 158, 11), width=2)
    draw.text((75, 63), "🛡️ LISANSARENA ARENA", font=f_badge, fill=(255, 215, 0))

    # Right Emerald Instant Delivery
    draw_rounded_rect(draw, [W-390, 50, W-55, 105], radius=14, fill=(6, 20, 14), outline=(16, 185, 129), width=2)
    draw.text((W-365, 63), "⚡ ANINDA AKTİVASYON", font=f_badge, fill=(52, 211, 153))

    # 3. Main Product Title (Clean Serif/San-Serif Headline)
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

    # 4. Gold Variant Ribbon
    var_y = start_y + len(lines[:2]) * 62 + 20
    f_var = get_font(FONT_BOLD, 30)
    var_label = f"👑  {variant}  👑"
    v_bbox = draw.textbbox((0, 0), var_label, font=f_var)
    v_w = v_bbox[2] - v_bbox[0] + 50
    draw_rounded_rect(draw, [60, var_y, 60 + v_w, var_y + 60], radius=12, fill=(217, 119, 6), outline=(255, 215, 0), width=2)
    draw.text((85, var_y + 11), var_label, font=f_var, fill=(255, 255, 255))

    # 5. Distinctive Arena Vault Armor Card (Centerpiece)
    card_y = var_y + 85
    card_h = 370
    draw_rounded_rect(draw, [60, card_y, W-60, card_y + card_h], radius=24, fill=(12, 12, 16), outline=(245, 158, 11), width=3)
    draw_rounded_rect(draw, [70, card_y + 10, W-70, card_y + card_h - 10], radius=18, fill=(18, 18, 24), outline=(255, 255, 255, 20), width=1)

    # Gold Arena Emblem on Card
    draw_rounded_rect(draw, [95, card_y + 35, 180, card_y + 115], radius=14, fill=(35, 26, 6), outline=(255, 215, 0), width=2)
    draw.text((115, card_y + 48), "LA", font=get_font(FONT_TITLE, 48), fill=(255, 215, 0))

    # Title & Sub inside Card
    draw.text((205, card_y + 42), "LISANSARENA PLATINUM", font=get_font(FONT_TITLE, 40), fill=(255, 255, 255))
    draw.text((205, card_y + 95), theme["tag"], font=get_font(FONT_BOLD, 21), fill=(251, 191, 36))

    # Features
    features = [
        "◆ Birebir LisansArena Telafi & Değişim Güvencesi",
        "◆ 7/24 Kesintisiz Canlı Telegram Destek (@LisansArena)",
        "◆ Güvenli 3D Shopier Alışverişi & Anında Cüzdan Bakiyesi"
    ]
    f_feat = get_font(FONT_BOLD, 25)
    for idx, feat in enumerate(features):
        fy = card_y + 175 + idx * 52
        draw.text((100, fy), feat, font=f_feat, fill=(240, 240, 245))

    # 6. Bottom Banner: Gold Guarantee Seal (Left) + Emerald Price Tag (Right)
    bot_y = card_y + card_h + 35

    # Gold Guarantee Shield (Left)
    draw_rounded_rect(draw, [60, bot_y, 460, bot_y + 115], radius=20, fill=(30, 22, 6), outline=(245, 158, 11), width=3)
    draw.text((85, bot_y + 20), "🛡️ %100 ORİJİNAL", font=get_font(FONT_BOLD, 30), fill=(255, 215, 0))
    draw.text((85, bot_y + 68), "LISANSARENA RESMİ GÜVENCE", font=get_font(FONT_BOLD, 18), fill=(217, 119, 6))

    # Emerald Price Tag (Right)
    draw_rounded_rect(draw, [W-470, bot_y, W-60, bot_y + 115], radius=20, fill=(6, 32, 20), outline=(16, 185, 129), width=3)
    draw.text((W-440, bot_y + 16), "ARENA FİYATI", font=get_font(FONT_BOLD, 20), fill=(110, 231, 183))
    draw.text((W-440, bot_y + 46), price, font=get_font(FONT_TITLE, 48), fill=(255, 255, 255))

    img.save(output_path, "JPEG", quality=95)
    return output_path

if __name__ == "__main__":
    links_path = BASE_DIR / "lisansarena_shopier_links.json"
    with open(links_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    print(f"[*] LisansArena için {len(raw_items)} adet ÖZEL ALTIN & ZÜMRÜT Kapak üretiliyor...")
    seen = set()
    la_products = []
    
    for item in raw_items:
        pid = str(item["id"])
        if pid in seen:
            continue
        seen.add(pid)
        
        out_name = f"la_gold_{pid}.jpg"
        out_path = LA_OUTPUT_DIR / out_name
        create_lisansarena_banner(item, str(out_path))

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
            "badge": "👑 Arena VIP" if is_showcase else "⚡ Orijinal",
            "url": item.get("url", f"https://www.shopier.com/lisansarena/{pid}"),
            "description": item.get("description", f"{title} - LisansArena güvencesiyle 7/24 anında teslimat ve telafi desteği."),
            "showcase": is_showcase,
            "is_vitrin": is_showcase
        }
        la_products.append(prod)
        print(f"[+] LisansArena Özel Altın Kapak: {title} -> {out_name}")

    out_db = LA_MINIAPP_DIR / "products_db.json"
    with open(out_db, "w", encoding="utf-8") as f:
        json.dump(la_products, f, ensure_ascii=False, indent=2)

    print(f"\n[✓] LisansArena'ya özel {len(la_products)} ürünün altın & zümrüt kapakları başarıyla üretildi!")
