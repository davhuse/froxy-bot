#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeyVadi Mini App — 61 Ürün İçin Profesyonel İlan Görseli Üretici Motoru
Her ürünün marka rengine, kategorisine, hesap türüne ve süresine özel 800x800 yüksek kaliteli grafikler üretir.
"""

import os
import sys
import json
import math
import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRODUCTS_JSON = os.path.join(BASE_DIR, "products_db.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "assets", "products")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load fonts
def get_font(name_type, size):
    font_paths = {
        "bold": ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"],
        "regular": ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"],
        "black": ["C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/segoeuib.ttf"]
    }
    for p in font_paths.get(name_type, font_paths["regular"]):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def safe_text(value):
    """Keep cover typography free of emoji glyph boxes on Windows fonts."""
    return "".join(ch for ch in str(value or "") if ord(ch) <= 0xFFFF and not 0xFE00 <= ord(ch) <= 0xFE0F)

# Brand Color Palettes & Icons
BRAND_CONFIGS = {
    "gemini": {
        "bg_glow": [(26, 115, 232), (0, 210, 255)],
        "accent": (0, 210, 255),
        "tag": "GOOGLE AI",
        "icon_text": "✦ GEMINI"
    },
    "grok": {
        "bg_glow": [(255, 69, 0), (255, 140, 0)],
        "accent": (255, 90, 30),
        "tag": "xAI GROK",
        "icon_text": "✕ GROK"
    },
    "chat gpt": {
        "bg_glow": [(16, 163, 127), (6, 182, 212)],
        "accent": (16, 185, 129),
        "tag": "OPENAI",
        "icon_text": "◉ CHATGPT"
    },
    "chatgpt": {
        "bg_glow": [(16, 163, 127), (6, 182, 212)],
        "accent": (16, 185, 129),
        "tag": "OPENAI",
        "icon_text": "◉ CHATGPT"
    },
    "canva": {
        "bg_glow": [(0, 196, 204), (125, 42, 232)],
        "accent": (0, 196, 204),
        "tag": "CANVA PRO",
        "icon_text": "🎨 CANVA"
    },
    "adobe": {
        "bg_glow": [(237, 28, 36), (180, 0, 20)],
        "accent": (255, 70, 70),
        "tag": "ADOBE CREATIVE",
        "icon_text": "▲ ADOBE"
    },
    "capcut": {
        "bg_glow": [(0, 229, 255), (59, 130, 246)],
        "accent": (0, 229, 255),
        "tag": "CAPCUT PRO",
        "icon_text": "✂ CAPCUT"
    },
    "gamma": {
        "bg_glow": [(139, 92, 246), (236, 72, 153)],
        "accent": (236, 72, 153),
        "tag": "GAMMA AI",
        "icon_text": "◆ GAMMA"
    },
    "netflix": {
        "bg_glow": [(229, 9, 20), (140, 0, 10)],
        "accent": (229, 9, 20),
        "tag": "NETFLIX 4K UHD",
        "icon_text": "■ NETFLIX"
    },
    "spotify": {
        "bg_glow": [(29, 185, 84), (10, 120, 50)],
        "accent": (29, 185, 84),
        "tag": "SPOTIFY PREMIUM",
        "icon_text": "♫ SPOTIFY"
    },
    "youtube": {
        "bg_glow": [(255, 0, 0), (180, 0, 0)],
        "accent": (255, 50, 50),
        "tag": "YOUTUBE PREMIUM",
        "icon_text": "▶ YOUTUBE"
    },
    "prime": {
        "bg_glow": [(0, 168, 225), (15, 60, 120)],
        "accent": (0, 168, 225),
        "tag": "PRIME VIDEO",
        "icon_text": "✓ PRIME"
    },
    "hbo": {
        "bg_glow": [(138, 43, 226), (88, 34, 180)],
        "accent": (168, 85, 247),
        "tag": "HBO MAX",
        "icon_text": "★ HBO MAX"
    },
    "crunchyroll": {
        "bg_glow": [(244, 117, 33), (255, 160, 0)],
        "accent": (244, 117, 33),
        "tag": "CRUNCHYROLL",
        "icon_text": "◎ CRUNCHY"
    },
    "duolingo": {
        "bg_glow": [(88, 204, 2), (20, 150, 0)],
        "accent": (88, 204, 2),
        "tag": "DUOLINGO SUPER",
        "icon_text": "🦉 DUO MAX"
    },
    "steam": {
        "bg_glow": [(102, 192, 244), (23, 26, 33)],
        "accent": (102, 192, 244),
        "tag": "STEAM RANDOM",
        "icon_text": "⚙ STEAM"
    },
    "xbox": {
        "bg_glow": [(16, 124, 16), (8, 70, 8)],
        "accent": (52, 211, 153),
        "tag": "XBOX GAME PASS",
        "icon_text": "🎮 XBOX"
    },
    "windows": {
        "bg_glow": [(0, 120, 215), (0, 70, 150)],
        "accent": (56, 189, 248),
        "tag": "MICROSOFT WINDOWS",
        "icon_text": "⊞ WINDOWS"
    },
    "office": {
        "bg_glow": [(216, 59, 1), (180, 40, 0)],
        "accent": (251, 146, 60),
        "tag": "OFFICE 365",
        "icon_text": "📄 OFFICE 365"
    },
    "kaspersky": {
        "bg_glow": [(0, 109, 85), (0, 160, 120)],
        "accent": (52, 211, 153),
        "tag": "KASPERSKY SECURITY",
        "icon_text": "🛡 KASPERSKY"
    },
    "trendyol": {
        "bg_glow": [(242, 122, 26), (200, 70, 0)],
        "accent": (251, 146, 60),
        "tag": "TRENDYOL İNDİRİM",
        "icon_text": "🏷 TRENDYOL"
    },
    "shell": {
        "bg_glow": [(251, 206, 7), (221, 29, 33)],
        "accent": (250, 204, 21),
        "tag": "SHELL PUAN",
        "icon_text": "⛽ SHELL CLUB"
    },
    "discord": {
        "bg_glow": [(88, 101, 242), (50, 60, 180)],
        "accent": (129, 140, 248),
        "tag": "DISCORD NITRO",
        "icon_text": "🚀 NITRO BOOST"
    },
    "fc26": {
        "bg_glow": [(0, 240, 255), (139, 92, 246)],
        "accent": (0, 240, 255),
        "tag": "EA SPORTS FC26",
        "icon_text": "⚽ FC26"
    },
    "zula": {
        "bg_glow": [(255, 230, 0), (255, 70, 0)],
        "accent": (250, 204, 21),
        "tag": "ZULA RANDOM",
        "icon_text": "🎯 ZULA HESAP"
    },
    "deepl": {
        "bg_glow": [(15, 43, 70), (14, 165, 233)],
        "accent": (56, 189, 248),
        "tag": "DEEPL PRO AI",
        "icon_text": "🌐 DEEPL AI"
    },
    "magnific": {
        "bg_glow": [(168, 85, 247), (236, 72, 153)],
        "accent": (236, 72, 153),
        "tag": "MAGNIFIC AI",
        "icon_text": "✨ MAGNIFIC"
    },
    "grammarly": {
        "bg_glow": [(21, 130, 89), (16, 185, 129)],
        "accent": (52, 211, 153),
        "tag": "GRAMMARLY PRO",
        "icon_text": "✍ GRAMMARLY"
    },
    "scribd": {
        "bg_glow": [(26, 124, 150), (15, 23, 42)],
        "accent": (56, 189, 248),
        "tag": "SCRIBD PREMIUM",
        "icon_text": "📚 SCRIBD"
    },
    "semrush": {
        "bg_glow": [(255, 100, 45), (255, 160, 0)],
        "accent": (255, 100, 45),
        "tag": "SEMRUSH PRO",
        "icon_text": "📊 SEMRUSH"
    }
}

def get_brand_config(title):
    t = title.lower()
    for key, cfg in BRAND_CONFIGS.items():
        if key in t:
            return cfg
    return {
        "bg_glow": [(6, 182, 212), (59, 130, 246)],
        "accent": (6, 182, 212),
        "tag": "KEYVADI DİJİTAL",
        "icon_text": "⚡ PREMIUM"
    }

def create_product_cover(product, output_path):
    W, H = 800, 800
    img = Image.new("RGB", (W, H), color=(10, 14, 26))
    draw = ImageDraw.Draw(img)

    title = product.get("title", "KeyVadi Ürün")
    price = product.get("price", "0 TL")
    badge = product.get("badge", "⭐ Popüler")
    cfg = get_brand_config(title)

    # 1. Base Gradient & Glow Circles
    glow1_color, glow2_color = cfg["bg_glow"]
    
    # Glow layer
    glow_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_img)
    
    # Top-right glow
    glow_draw.ellipse([450, -100, 950, 400], fill=(glow1_color[0], glow1_color[1], glow1_color[2], 90))
    # Bottom-left glow
    glow_draw.ellipse([-150, 450, 400, 950], fill=(glow2_color[0], glow2_color[1], glow2_color[2], 80))
    # Center subtle glow
    glow_draw.ellipse([200, 200, 600, 600], fill=(cfg["accent"][0], cfg["accent"][1], cfg["accent"][2], 40))

    glow_img = glow_img.filter(ImageFilter.GaussianBlur(80))
    img.paste(glow_img, (0, 0), glow_img)

    # 2. Main Glassmorphism Card Frame
    card_x0, card_y0, card_x1, card_y1 = 40, 40, W - 40, H - 40
    
    # Translucent card body
    card_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_layer)
    card_draw.rounded_rectangle([card_x0, card_y0, card_x1, card_y1], radius=32, fill=(15, 23, 42, 200), outline=(255, 255, 255, 30), width=2)
    
    # Inner border glow
    card_draw.rounded_rectangle([card_x0 + 4, card_y0 + 4, card_x1 - 4, card_y1 - 4], radius=28, outline=(cfg["accent"][0], cfg["accent"][1], cfg["accent"][2], 50), width=1)
    img.paste(card_layer, (0, 0), card_layer)

    # 3. Top Header Bar
    font_small = get_font("bold", 20)
    font_tag = get_font("bold", 22)
    font_brand = get_font("black", 42)
    font_title = get_font("bold", 34)
    font_price = get_font("black", 46)
    font_footer = get_font("bold", 19)

    # Brand Pill (Top Left)
    draw.rounded_rectangle([70, 70, 290, 115], radius=14, fill=(20, 30, 50, 255), outline=cfg["accent"], width=2)
    draw.text((90, 80), "KEYVADİ", font=font_small, fill=(255, 255, 255))
    draw.text((215, 80), "VIP", font=font_small, fill=cfg["accent"])

    # Product type pill; avoid promising delivery or warranty on a static cover.
    draw.rounded_rectangle([W - 310, 70, W - 70, 115], radius=14, fill=(10, 35, 30, 255), outline=cfg["accent"], width=2)
    draw.text((W - 290, 80), "DİJİTAL ÜRÜN", font=font_small, fill=cfg["accent"])

    # 4. Central Hero Brand Emblem Card
    emblem_w, emblem_h = 440, 140
    emblem_x0 = (W - emblem_w) // 2
    emblem_y0 = 160
    emblem_x1 = emblem_x0 + emblem_w
    emblem_y1 = emblem_y0 + emblem_h

    # Glowing emblem backdrop
    draw.rounded_rectangle([emblem_x0, emblem_y0, emblem_x1, emblem_y1], radius=24, fill=(10, 16, 32, 240), outline=cfg["accent"], width=2)
    
    # Emblem Tag
    draw.text((emblem_x0 + 24, emblem_y0 + 18), cfg["tag"], font=font_tag, fill=cfg["accent"])
    # Emblem Main Text
    draw.text((emblem_x0 + 24, emblem_y0 + 55), safe_text(cfg["icon_text"]), font=font_brand, fill=(255, 255, 255))

    # 5. Product Title with Word Wrap
    title_clean = title.strip()
    words = title_clean.split()
    lines = []
    curr_line = ""
    for w in words:
        test_line = f"{curr_line} {w}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font_title)
        if bbox[2] - bbox[0] < (W - 140):
            curr_line = test_line
        else:
            if curr_line:
                lines.append(curr_line)
            curr_line = w
    if curr_line:
        lines.append(curr_line)

    lines = lines[:3] # Max 3 lines
    start_y = 340
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        line_w = bbox[2] - bbox[0]
        draw.text(((W - line_w) // 2, start_y), line, font=font_title, fill=(248, 250, 252))
        start_y += 48

    # 6. Type & Warranty Badge
    badge_label = badge.replace('✨', '').replace('👥', '').replace('🎲', '').replace('⚡', '').replace('⭐', '').strip()
    if badge_label.lower() in {"hızlı teslimat", "garantili", "garanti"}:
        badge_label = "ÖNE ÇIKAN"
    badge_text = f"{safe_text(badge_label)}  •  GÜNCEL ÜRÜN"
    bbox_b = draw.textbbox((0, 0), badge_text, font=font_small)
    bw = bbox_b[2] - bbox_b[0] + 36
    bx0 = (W - bw) // 2
    by0 = start_y + 15
    draw.rounded_rectangle([bx0, by0, bx0 + bw, by0 + 44], radius=22, fill=(255, 255, 255, 15), outline=(255, 255, 255, 40), width=1)
    draw.text((bx0 + 18, by0 + 9), badge_text, font=font_small, fill=(203, 213, 225))

    # 7. Price Box (Bottom Big Highlight)
    price_box_w, price_box_h = 660, 95
    px0 = (W - price_box_w) // 2
    py0 = H - 200
    px1 = px0 + price_box_w
    py1 = py0 + price_box_h

    draw.rounded_rectangle([px0, py0, px1, py1], radius=20, fill=(6, 18, 30), outline=(52, 211, 153), width=2)
    
    # Left Label
    draw.text((px0 + 25, py0 + 16), "İNDİRİMLİ FİYAT:", font=font_small, fill=(148, 163, 184))
    draw.text((px0 + 25, py0 + 48), "Güvenli ödeme seçeneği", font=font_small, fill=(52, 211, 153))

    # Right Big Price
    price_bbox = draw.textbbox((0, 0), price, font=font_price)
    pw = price_bbox[2] - price_bbox[0]
    draw.text((px1 - pw - 25, py0 + 20), price, font=font_price, fill=(52, 211, 153))

    # 8. Bottom Secure Ribbon
    footer_text = "KEYVADİ MAĞAZASI • GÜVENLİ ÖDEME"
    f_bbox = draw.textbbox((0, 0), footer_text, font=font_footer)
    fw = f_bbox[2] - f_bbox[0]
    draw.text(((W - fw) // 2, H - 75), footer_text, font=font_footer, fill=(100, 116, 139))

    img.save(output_path, "PNG", quality=95)

def main():
    print("=" * 60)
    print("🎨 KEYVADI MINI APP İLAN GÖRSELİ ÜRETİM MOTORU")
    print("=" * 60)

    if not os.path.exists(PRODUCTS_JSON):
        print(f"HATA: {PRODUCTS_JSON} bulunamadı!")
        return

    with open(PRODUCTS_JSON, "r", encoding="utf-8") as f:
        products = json.load(f)

    print(f"Toplam {len(products)} ürün için özel görsel hazırlanıyor...\n")

    for i, p in enumerate(products):
        pid = str(p.get("id"))
        filename = f"product_{pid}.png"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        create_product_cover(p, filepath)
        p["image"] = f"assets/products/{filename}"
        print(f"[{i+1}/{len(products)}] ✅ {p['title'][:40]} -> {filename}")

    # Save updated products_db.json
    with open(PRODUCTS_JSON, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"🎉 61 ÜRÜNÜN TAMAMI İÇİN ÖZEL GÖRSELLER ÜRETİLDİ!")
    print(f"📁 Dizin: {OUTPUT_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
