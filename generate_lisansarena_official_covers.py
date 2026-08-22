#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LisansArena — Resmi Şablon Kapak Motoru (v8.0)
Kullanıcının yüklediği resmi 'LİSANSARENA BAKİYE YÜKLEME' şablonuna %100 sadık kalarak:
1. Bakiye Yükleme kapaklarını (25, 50, 100, 250, 500, 1000 TL ve Özel Tutar)
2. Tüm 34 LisansArena ürününün kapaklarını (3D AI görsel + Resmi Şablon çerçevesi)
yüksek çözünürlükte üretir.
"""

import os
import sys
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path("C:/Users/habil/.gemini/antigravity/brain/b3d6b142-698f-408f-8efb-52bc1b303e13")
REF_IMG_PATH = ARTIFACT_DIR / ".user_uploaded" / "media_1787190372601.jpg"

LA_MINIAPP_DIR = BASE_DIR / "miniapp_lisansarena"
LA_OUTPUT_DIR = LA_MINIAPP_DIR / "assets" / "products"
LA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TOPUP_DIR = LA_MINIAPP_DIR / "assets" / "topups"
TOPUP_DIR.mkdir(parents=True, exist_ok=True)

FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
FONT_TITLE = "C:/Windows/Fonts/arialbd.ttf"
FONT_REGULAR = "C:/Windows/Fonts/segoeui.ttf"

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def draw_official_price_box(draw, bbox, price_text, f_price):
    """Kullanıcının yüklediği şablondaki Mavi/Altın Çift Işıklı Çerçeveyi ve 3D Altın Yazıyı çizer."""
    x1, y1, x2, y2 = bbox
    r = 28
    
    # Outer neon glow
    for g in range(6, 0, -1):
        # Left blue glow, right gold glow
        draw.rounded_rectangle([x1-g, y1-g, x2+g, y2+g], radius=r+g, outline=(0, 180, 255, 30), width=1)
        draw.rounded_rectangle([x1-g+100, y1-g, x2+g, y2+g], radius=r+g, outline=(255, 180, 0, 30), width=1)

    # Main dark pill background
    draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=(12, 14, 30), outline=None)
    
    # Border: Left blue, Right gold
    draw.rounded_rectangle([x1, y1, x2, y2], radius=r, outline=(0, 200, 255), width=3)
    draw.rounded_rectangle([x1 + int((x2-x1)*0.55), y1, x2, y2], radius=r, outline=(255, 190, 20), width=3)

    # 3D Gold Embossed Price Text
    p_bbox = draw.textbbox((0, 0), price_text, font=f_price)
    pw = p_bbox[2] - p_bbox[0]
    ph = p_bbox[3] - p_bbox[1]
    px = x1 + (x2 - x1 - pw) / 2
    py = y1 + (y2 - y1 - ph) / 2 - 4

    # Drop shadow
    draw.text((px + 3, py + 4), price_text, font=f_price, fill=(5, 5, 10))
    draw.text((px + 2, py + 3), price_text, font=f_price, fill=(120, 80, 10))
    # Gold face
    draw.text((px, py), price_text, font=f_price, fill=(255, 215, 60))
    # Top highlight
    draw.text((px - 1, py - 1), price_text, font=f_price, fill=(255, 245, 180))

def create_topup_banner(amount_text, output_path):
    """Resmi Cüzdan görselinin üzerine istenen tutarı monte eder."""
    if REF_IMG_PATH.exists():
        img = Image.open(REF_IMG_PATH).convert("RGBA").resize((1000, 1000), Image.Resampling.LANCZOS)
    else:
        img = Image.new("RGBA", (1000, 1000), (8, 10, 24, 255))

    draw = ImageDraw.Draw(img)
    f_price = get_font(FONT_TITLE, 76)

    # Bottom price box
    bbox = [70, 710, 930, 880]
    draw_official_price_box(draw, bbox, amount_text, f_price)

    img.convert("RGB").save(output_path, "JPEG", quality=95)
    return output_path

def create_product_banner(product, ai_image_path, output_path):
    """Ürünün 3D AI görselini Resmi LisansArena Şablonuna entegre eder."""
    W, H = 1000, 1000
    img = Image.new("RGBA", (W, H), (8, 10, 24, 255))
    draw = ImageDraw.Draw(img)

    # 1. Dark Indigo/Purple Cyber Circuit Background
    for y in range(H):
        ratio = y / H
        r = int(14 * (1 - ratio) + 6 * ratio)
        g = int(18 * (1 - ratio) + 8 * ratio)
        b = int(48 * (1 - ratio) + 20 * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

    # Circuit Lines
    for cy in range(60, 400, 35):
        draw.line([(0, cy), (W, cy)], fill=(0, 200, 255, 12), width=1)
    for cx in range(80, W, 70):
        draw.line([(cx, 0), (cx, 400)], fill=(99, 102, 241, 10), width=1)

    # 2. Top Header (Silver LİSANSARENA + Gold Subtitle)
    f_brand = get_font(FONT_TITLE, 52)
    f_sub = get_font(FONT_TITLE, 34)

    # "LİSANSARENA"
    b_text = "LİSANSARENA"
    bb = draw.textbbox((0, 0), b_text, font=f_brand)
    bx = (W - (bb[2] - bb[0])) / 2
    draw.text((bx + 2, 52), b_text, font=f_brand, fill=(10, 10, 20))
    draw.text((bx, 50), b_text, font=f_brand, fill=(240, 245, 255))

    # Category / Title Subtitle in Gold
    title = product.get("title", "DİJİTAL LİSANS")
    short_title = title.split("(")[0].strip().upper()
    if len(short_title) > 26:
        short_title = short_title[:24] + "..."
    sb = draw.textbbox((0, 0), short_title, font=f_sub)
    sx = (W - (sb[2] - sb[0])) / 2
    draw.text((sx + 2, 114), short_title, font=f_sub, fill=(15, 10, 5))
    draw.text((sx, 112), short_title, font=f_sub, fill=(245, 190, 40))

    # 3. Center 3D AI Product Visual (On podium)
    if ai_image_path and Path(ai_image_path).exists():
        try:
            prod_img = Image.open(ai_image_path).convert("RGBA")
            # Crop center
            pw, ph = prod_img.size
            dim = min(pw, ph)
            prod_img = prod_img.crop(((pw-dim)//2, (ph-dim)//2, (pw+dim)//2, (ph+dim)//2))
            prod_img = prod_img.resize((540, 540), Image.Resampling.LANCZOS)
            
            # Rounded mask with glow
            mask = Image.new("L", (540, 540), 0)
            m_draw = ImageDraw.Draw(mask)
            m_draw.rounded_rectangle([0, 0, 540, 540], radius=32, fill=255)
            
            img.paste(prod_img, (230, 160), mask)
            
            # Gold/Blue Frame around product
            draw.rounded_rectangle([228, 158, 772, 702], radius=34, outline=(0, 200, 255), width=3)
        except Exception as e:
            print("Product paste error:", e)

    # 4. Bottom Official Price Box
    price_text = product.get("price", "₺49.90").replace("TL", "").replace("₺", "").strip() + " TL"
    f_price = get_font(FONT_TITLE, 70 if len(price_text) > 8 else 76)
    bbox = [70, 725, 930, 890]
    draw_official_price_box(draw, bbox, price_text, f_price)

    img.convert("RGB").save(output_path, "JPEG", quality=95)
    return output_path

if __name__ == "__main__":
    print("[*] 1. LisansArena Resmi Bakiye Yükleme Şablonları Üretiliyor...")
    topup_amounts = ["25 TL", "50 TL", "100 TL", "250 TL", "500 TL", "1.000 TL", "ÖZEL TUTAR"]
    for amt in topup_amounts:
        safe_name = amt.replace(" ", "_").replace(".", "").replace("Ö", "O").lower()
        out_p = TOPUP_DIR / f"la_topup_{safe_name}.jpg"
        create_topup_banner(amt, str(out_p))
        print(f" [✓] Bakiye Kapak: {amt} -> {out_p.name}")

    print("\n[*] 2. 34 LisansArena Ürünü İçin Resmi Şablonlu Kapaklar Üretiliyor...")
    links_path = BASE_DIR / "lisansarena_shopier_links.json"
    with open(links_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    # Find matching AI images
    def find_art(name):
        matches = list(ARTIFACT_DIR.glob(f"{name}_*.jpg"))
        if matches:
            matches.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return str(matches[0])
        return None

    ai_sources = {
        "canva": find_art("la_canva_pro_ai"),
        "gemini": find_art("la_gemini_ultra_ai"),
        "fc26": find_art("la_fc26_ai"),
        "windows": find_art("la_windows_office_ai"),
        "office": find_art("la_windows_office_ai"),
        "grok": find_art("la_grok_ai"),
        "steam": find_art("la_steam_ai"),
        "telegram": find_art("la_telegram_ai"),
        "zula": find_art("la_zula_ai"),
        "chatgpt": find_art("la_chatgpt_ai"),
        "adobe": find_art("la_adobe_cc_ai"),
        "netflix": find_art("la_netflix_ai"),
        "perplexity": find_art("la_perplexity_ai"),
        "shell": find_art("la_shell_fuel_ai"),
        "crunchyroll": find_art("la_crunchyroll_ai")
    }

    seen = set()
    la_products = []

    for item in raw_items:
        pid = str(item["id"])
        if pid in seen:
            continue
        seen.add(pid)

        title = item["title"]
        price = item["price"]
        clean_p = price.replace("TL", "").replace("₺", "").strip().replace(".", "").replace(",", ".")
        try:
            p_num = float(clean_p)
        except Exception:
            p_num = 0.0

        t_low = title.lower()

        # Find best AI visual
        matched_ai = None
        for k in ai_sources:
            if k in t_low and ai_sources[k]:
                matched_ai = ai_sources[k]
                break
        if not matched_ai:
            matched_ai = ai_sources["gemini"]

        out_name = f"la_banner_{pid}.jpg"
        out_path = LA_OUTPUT_DIR / out_name
        create_product_banner(item, matched_ai, str(out_path))

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
        print(f" [✓] Ürün Kapağı: {title} -> {out_name}")

    out_db = LA_MINIAPP_DIR / "products_db.json"
    with open(out_db, "w", encoding="utf-8") as f:
        json.dump(la_products, f, ensure_ascii=False, indent=2)

    print("\n[✓] LisansArena için tüm kapaklar ve bakiye yükleme şablonları başarıyla tamamlandı!")
