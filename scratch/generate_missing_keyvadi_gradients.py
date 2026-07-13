import os
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\static"

missing_products = [
    {"name": "Eski Tarihli Telegram Hesabı (+1 No'lu)", "category": "Numbers", "slug": "telegram_account"},
    {"name": "Perplexity Pro (1 Aylık Hesap)", "category": "AI", "slug": "perplexity_pro"},
    {"name": "DeepL AI (1 Aylık) - Kişisel Hesap", "category": "AI", "slug": "deepl_kisisel"},
    {"name": "DeepL AI (1 Aylık) - Ortak Hesap", "category": "AI", "slug": "deepl_ortak"},
    {"name": "Scribd (1 Aylık) - Kişisel Hesap", "category": "Design", "slug": "scribd_kisisel"},
    {"name": "Scribd (1 Aylık) - Ortak Hesap", "category": "Design", "slug": "scribd_ortak"},
    {"name": "Magnific AI Ortak (1 Aylık Business Hesap)", "category": "AI", "slug": "magnific_ai"},
    {"name": "Crunchyroll Özel Profil (1 Aylık)", "category": "Entertainment", "slug": "crunchyroll_ozel"},
    {"name": "Crunchyroll Ortak Hesap (1 Aylık)", "category": "Entertainment", "slug": "crunchyroll_ortak"},
    {"name": "Grammarly Pro (1 Haftalık) - Kendi Hesabınıza", "category": "Design", "slug": "grammarly_haftalik"},
    {"name": "Grammarly Pro (1 Aylık) - Ortak Hesap", "category": "Design", "slug": "grammarly_ortak"}
]

def create_gradient_png(title, category, filename):
    w, h = 800, 800
    
    if category == "AI":
        c1, c2 = (24, 18, 59), (89, 56, 172)
        cat_turkish = "YAPAY ZEKA (AI)"
    elif category == "Entertainment":
        c1, c2 = (60, 6, 6), (180, 20, 20)
        cat_turkish = "EĞLENCE & MÜZİK"
    elif category == "Design":
        c1, c2 = (10, 48, 70), (25, 120, 160)
        cat_turkish = "TASARIM & YAZILIM"
    elif category == "Numbers":
        c1, c2 = (15, 60, 40), (45, 150, 90)
        cat_turkish = "ONAYLI NUMARA & MAİL"
    elif category == "Coupons":
        c1, c2 = (80, 45, 10), (190, 120, 30)
        cat_turkish = "KUPON & İNDİRİM"
    else:
        c1, c2 = (30, 30, 30), (80, 80, 80)
        cat_turkish = "DİJİTAL ÜRÜN"
        
    base = Image.new("RGB", (w, h), c1)
    draw = ImageDraw.Draw(base)
    
    # Draw vertical gradient
    for y in range(h):
        r = int(c1[0] + (c2[0] - c1[0]) * y / h)
        g = int(c1[1] + (c2[1] - c1[1]) * y / h)
        b = int(c1[2] + (c2[2] - c1[2]) * y / h)
        draw.line((0, y, w, y), fill=(r, g, b))
        
    card_margin = 85
    draw.rounded_rectangle(
        [(card_margin, card_margin), (w - card_margin, h - card_margin)],
        radius=35,
        fill=(0, 0, 0, 110),
        outline=(255, 255, 255, 35),
        width=3
    )
    
    font_path = "arial.ttf"
    try:
        font_title = ImageFont.truetype(font_path, 38)
        font_sub = ImageFont.truetype(font_path, 23)
        font_badge = ImageFont.truetype(font_path, 17)
    except IOError:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        
    draw.text((w/2, 170), cat_turkish, font=font_badge, fill=(200, 220, 255), anchor="mm")
    
    words = title.split()
    lines = []
    current_line = []
    for word in words:
        if len(" ".join(current_line + [word])) * 17 < (w - card_margin * 3.5):
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    y_text = 360 - (len(lines) - 1) * 25
    for line in lines[:3]:
        draw.text((w/2, y_text), line, font=font_title, fill=(255, 255, 255), anchor="mm")
        y_text += 55
        
    draw.text((w/2, 595), "ANINDA DİJİTAL TESLİMAT", font=font_sub, fill=(160, 255, 160), anchor="mm")
    draw.text((w/2, 635), "GÜVENLİ ÖDEME | %100 GARANTİLİ", font=font_sub, fill=(225, 225, 225), anchor="mm")
    
    # Save as PNG (we name it .jpg to match create_shopier_products_api expected extension or we can save as PNG and update references)
    # The Shopier API supports both PNG and JPG. Let's save as PNG but name it .png or .jpg, let's use .png for higher quality!
    base.save(filename, "PNG")

if __name__ == "__main__":
    print("Generating KeyVadi Gradient Cover Images...")
    for idx, p in enumerate(missing_products):
        filename = os.path.join(OUTPUT_DIR, f"keyvadi_{p['slug']}.png")
        create_gradient_png(p["name"], p["category"], filename)
        print(f"Generated: {filename}")
    print("All cover images generated successfully in KeyVadi style!")
