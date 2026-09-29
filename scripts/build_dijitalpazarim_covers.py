# -*- coding: utf-8 -*-
"""Generate high-aesthetic purple-neon product covers for Dijital Pazarım brand."""

from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
MINIAPP_PRODUCTS_DIR = ROOT / "miniapp_dijitalpazarim" / "assets" / "products"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
MINIAPP_PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)

SIZE = 1000
FONT_REGULAR = Path("C:/Windows/Fonts/segoeui.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/segoeuib.ttf")
FONT_BLACK = Path("C:/Windows/Fonts/ariblk.ttf")

PRODUCTS = [
    {
        "filename": "dp_trendyol_go.jpg",
        "brand_title": "TRENDYOL GO",
        "sub_title": "800 / 300 TL İNDİRİM",
        "category": "MARKET KUPONU",
        "highlight": "800 TL Üzeri 300 TL Anında İndirim",
        "price": "44,99 TL",
        "tag": "ANINDA KULLANIM",
        "accent": (168, 85, 247), # Neon purple
        "sec_accent": (236, 72, 153) # Hot pink
    },
    {
        "filename": "dp_trendyol_yemek.jpg",
        "brand_title": "TRENDYOL YEMEK",
        "sub_title": "750 / 250 TL İNDİRİM",
        "category": "YEMEK KUPONU",
        "highlight": "750 TL Üzeri 250 TL Anında İndirim",
        "price": "44,99 TL",
        "tag": "ANINDA KULLANIM",
        "accent": (168, 85, 247),
        "sec_accent": (249, 115, 22)
    },
    {
        "filename": "dp_shell_75.jpg",
        "brand_title": "SHELL CLUB SMART",
        "sub_title": "75 TL YAKIT PUANI",
        "category": "AKARYAKIT & OTOGAZ",
        "highlight": "İstasyonlarda Geçerli 75 TL Puan",
        "price": "19,99 TL",
        "tag": "HIZLI TESLİMAT",
        "accent": (168, 85, 247),
        "sec_accent": (234, 179, 8)
    },
    {
        "filename": "dp_uber_1000.jpg",
        "brand_title": "UBER YOLCULUK",
        "sub_title": "1.000 TL İNDİRİM PAKETİ",
        "category": "ULAŞIM KODU",
        "highlight": "2 Adet 500 TL (Toplam 1.000 TL) İndirim",
        "price": "49,99 TL",
        "tag": "SÜPER FIRSAT",
        "accent": (168, 85, 247),
        "sec_accent": (56, 189, 248)
    },
    {
        "filename": "dp_youtube_3m.jpg",
        "brand_title": "YOUTUBE PREMIUM",
        "sub_title": "3 AY KESİNTİSİZ",
        "category": "REKLAMSIZ MÜZİK & VİDEO",
        "highlight": "Kendi Hesabınıza Özel Aktivasyon Kodu",
        "price": "49,99 TL",
        "tag": "BİREYSEL KOD",
        "accent": (168, 85, 247),
        "sec_accent": (239, 68, 68)
    },
    {
        "filename": "dp_spotify_4m.jpg",
        "brand_title": "SPOTIFY PREMIUM",
        "sub_title": "4 AY BİREYSEL KOD",
        "category": "MÜZİK & PODCAST",
        "highlight": "Kesintisiz Reklamsız Müzik Keyfi",
        "price": "44,99 TL",
        "tag": "4 AY GARANTİLİ",
        "accent": (168, 85, 247),
        "sec_accent": (34, 197, 94)
    },
    {
        "filename": "dp_gemini_18m_5inv.jpg",
        "brand_title": "GEMINI PRO AI",
        "sub_title": "18 AY + 5 DAVET HAKKI",
        "category": "GOOGLE YAPAY ZEKA",
        "highlight": "Google One 2TB & Gemini Advanced",
        "price": "144,99 TL",
        "tag": "VIP PAKET",
        "accent": (168, 85, 247),
        "sec_accent": (96, 165, 250)
    },
    {
        "filename": "dp_gemini_18m.jpg",
        "brand_title": "GEMINI PRO AI",
        "sub_title": "18 AYLIK DAVET BAĞLANTISI",
        "category": "GOOGLE YAPAY ZEKA",
        "highlight": "Kendi Google Hesabınıza 18 Ay Tanımlama",
        "price": "74,99 TL",
        "tag": "18 AY ERİŞİM",
        "accent": (168, 85, 247),
        "sec_accent": (147, 51, 234)
    },
    {
        "filename": "dp_gemini_12m.jpg",
        "brand_title": "GEMINI PRO AI",
        "sub_title": "12 AYLIK DAVET BAĞLANTISI",
        "category": "GOOGLE YAPAY ZEKA",
        "highlight": "Kendi Google Hesabınıza 12 Ay Tanımlama",
        "price": "99,99 TL",
        "tag": "12 AY ERİŞİM",
        "accent": (168, 85, 247),
        "sec_accent": (192, 132, 252)
    },
    {
        "filename": "dp_gemini_1m.jpg",
        "brand_title": "GEMINI PRO AI",
        "sub_title": "1 AYLIK DAVET BAĞLANTISI",
        "category": "GOOGLE YAPAY ZEKA",
        "highlight": "Hızlı Başlangıç Kişisel Davet Kodu",
        "price": "49,99 TL",
        "tag": "1 AY ERİŞİM",
        "accent": (168, 85, 247),
        "sec_accent": (168, 85, 247)
    },
    {
        "filename": "dp_disney_ortak.jpg",
        "brand_title": "DISNEY+ 4K UHD",
        "sub_title": "1 AYLIK ORTAK HESAP",
        "category": "DİZİ & FİLM PLATFORMU",
        "highlight": "4K Ultra HD • 30 Gün Kesintisiz Telafi",
        "price": "49,90 TL",
        "tag": "FIRSAT ÜRÜNÜ",
        "accent": (168, 85, 247),
        "sec_accent": (56, 189, 248)
    },
    {
        "filename": "dp_disney_ozel.jpg",
        "brand_title": "DISNEY+ 4K UHD",
        "sub_title": "1 AYLIK ÖZEL PROFİL",
        "category": "DİZİ & FİLM PLATFORMU",
        "highlight": "PIN Korumalı Kişisel Profil • 30 Gün Telafi",
        "price": "99,90 TL",
        "tag": "KİŞİSEL PROFİL",
        "accent": (168, 85, 247),
        "sec_accent": (192, 132, 252)
    },
    {
        "filename": "dp_netflix_ozel.jpg",
        "brand_title": "NETFLIX 4K UHD",
        "sub_title": "KİŞİSEL ÖZEL PROFİL",
        "category": "DİZİ & FİLM PLATFORMU",
        "highlight": "PIN Korumalı Profil • 30 Gün Kesintisiz Telafi",
        "price": "79,90 TL",
        "tag": "30 GÜN GARANTİLİ",
        "accent": (168, 85, 247),
        "sec_accent": (239, 68, 68)
    }
]

def get_font(size: int, bold: bool = False, black: bool = False) -> ImageFont.FreeTypeFont:
    if black and FONT_BLACK.exists():
        return ImageFont.truetype(str(FONT_BLACK), size)
    p = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(str(p), size)

# Load brand logo thumbnail if available
logo_img = None
logo_path = STATIC_DIR / "dijitalpazarim_logo.jpg"
if logo_path.exists():
    try:
        raw_logo = Image.open(logo_path).convert("RGBA")
        # Resize to 130x130 with circular mask
        raw_logo = raw_logo.resize((130, 130), Image.Resampling.LANCZOS)
        mask = Image.new("L", (130, 130), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, 130, 130), fill=255)
        logo_img = Image.new("RGBA", (130, 130), (0, 0, 0, 0))
        logo_img.paste(raw_logo, (0, 0), mask=mask)
    except Exception as e:
        print("Logo load failed:", e)

def build_cover(item: dict):
    img = Image.new("RGB", (SIZE, SIZE))
    pixels = img.load()
    
    accent = item["accent"]
    sec = item["sec_accent"]
    
    # 1. Dark luxury background with purple radial gradient
    for y in range(SIZE):
        ty = y / (SIZE - 1)
        for x in range(SIZE):
            tx = x / (SIZE - 1)
            dist = math.sqrt((x - 500)**2 + (y - 380)**2) / 600.0
            radial = max(0.0, 1.0 - dist)
            
            r = int(9 + 10 * (1 - ty) + accent[0] * radial * 0.16 + sec[0] * (1 - dist if dist < 1 else 0) * 0.05)
            g = int(6 + 8 * (1 - ty) + accent[1] * radial * 0.10 + sec[1] * (1 - dist if dist < 1 else 0) * 0.04)
            b = int(22 + 20 * (1 - ty) + accent[2] * radial * 0.22 + sec[2] * (1 - dist if dist < 1 else 0) * 0.06)
            pixels[x, y] = (min(255, r), min(255, g), min(255, b))
            
    # 2. Glowing aura overlay
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((200, 160, 800, 720), fill=(*accent, 45))
    gd.ellipse((280, 240, 720, 640), fill=(*sec, 30))
    glow = glow.filter(ImageFilter.GaussianBlur(50))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    
    draw = ImageDraw.Draw(img)
    
    # 3. Outer boundary neon border
    draw.rounded_rectangle((35, 35, SIZE - 35, SIZE - 35), radius=36, outline=(*accent, 160), width=3)
    draw.rounded_rectangle((42, 42, SIZE - 42, SIZE - 42), radius=30, outline=(255, 255, 255, 30), width=1)
    
    # 4. Header Section: Brand name & Tag
    # Brand logo at top left
    if logo_img:
        img.paste(logo_img, (60, 60), mask=logo_img)
        draw.text((205, 80), "DİJİTAL PAZARIM", font=get_font(34, bold=True), fill=(255, 255, 255))
        draw.text((205, 125), "KOD • KUPON • DİJİTAL HESAP", font=get_font(18, bold=True), fill=(*accent, 255))
    else:
        draw.text((70, 75), "DİJİTAL PAZARIM", font=get_font(36, bold=True), fill=(255, 255, 255))
        draw.text((70, 125), "KOD • KUPON • DİJİTAL HESAP", font=get_font(18, bold=True), fill=(*accent, 255))
        
    # Top right category badge
    cat_text = item["category"]
    cat_font = get_font(20, bold=True)
    cat_bbox = draw.textbbox((0, 0), cat_text, font=cat_font)
    cat_w = cat_bbox[2] - cat_bbox[0] + 36
    draw.rounded_rectangle((SIZE - 65 - cat_w, 75, SIZE - 65, 125), radius=18, fill=(35, 18, 55, 230), outline=(*accent, 220), width=2)
    draw.text((SIZE - 65 - cat_w + 18, 87), cat_text, font=cat_font, fill=(245, 235, 255))
    
    # 5. Central Product Card
    draw.rounded_rectangle((65, 220, SIZE - 65, 690), radius=32, fill=(18, 11, 35, 220), outline=(*accent, 120), width=2)
    
    # Tag pill inside central card
    tag_text = item["tag"]
    tag_font = get_font(22, bold=True)
    t_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
    t_w = t_bbox[2] - t_bbox[0] + 32
    draw.rounded_rectangle((500 - t_w // 2, 260, 500 + t_w // 2, 308), radius=16, fill=(*sec, 50), outline=(*sec, 220), width=2)
    draw.text((500, 284), tag_text, font=tag_font, fill=(255, 255, 255), anchor="mm")
    
    # Brand Title
    draw.text((500, 370), item["brand_title"], font=get_font(62, bold=True), fill=(255, 255, 255), anchor="mm")
    
    # Sub Title
    draw.text((500, 455), item["sub_title"], font=get_font(46, bold=True), fill=(*sec, 255), anchor="mm")
    
    # Highlight feature
    draw.text((500, 535), item["highlight"], font=get_font(26, bold=False), fill=(220, 215, 240), anchor="mm")
    
    # Trust line
    trust_text = "Hızlı Teslimat   •   %100 Çalışma Garantisi   •   7/24 Canlı Destek"
    draw.text((500, 620), trust_text, font=get_font(21, bold=True), fill=(168, 160, 200), anchor="mm")
    
    # 6. Bottom Price Banner (Large, High Impact)
    draw.rounded_rectangle((65, 730, SIZE - 65, 930), radius=32, fill=(28, 14, 52, 240), outline=(*accent, 220), width=3)
    
    # Price
    price_str = item["price"]
    draw.text((500, 805), price_str, font=get_font(72, bold=True), fill=(255, 255, 255), anchor="mm")
    
    # Bottom Subtitle
    draw.text((500, 885), "GÜVENLİ SHOPIER ÖDEME ALTYAPISI", font=get_font(22, bold=True), fill=(*accent, 255), anchor="mm")
    
    # Save outputs
    rgb_img = img.convert("RGB")
    static_file = STATIC_DIR / item["filename"]
    miniapp_file = MINIAPP_PRODUCTS_DIR / item["filename"]
    
    rgb_img.save(static_file, "JPEG", quality=92, optimize=True)
    rgb_img.save(miniapp_file, "JPEG", quality=92, optimize=True)
    print(f"Saved: {item['filename']}")

if __name__ == "__main__":
    print(f"Generating {len(PRODUCTS)} covers for Dijital Pazarım...")
    for p in PRODUCTS:
        build_cover(p)
    print("All covers generated successfully!")
