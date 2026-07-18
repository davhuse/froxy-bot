import os
from PIL import Image, ImageDraw, ImageFont

static_dir = r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\static"

target_images = [
    {
        "filename": "lisansarena_exxen.png",
        "title": "Exxen Premium\n(1 Aylık Hesap)",
        "category": "EĞLENCE & MÜZİK",
        "grad_start": (60, 6, 6),
        "grad_end": (180, 20, 20),
        "badge_color": (255, 200, 200)
    },
    {
        "filename": "lisansarena_trendyol_yemek.png",
        "title": "Trendyol Yemek\n(150/100 İndirim)",
        "category": "KUPON & İNDİRİM",
        "grad_start": (80, 45, 10),
        "grad_end": (190, 120, 30),
        "badge_color": (255, 230, 200)
    },
    {
        "filename": "lisansarena_trendyol_market.png",
        "title": "Trendyol Market\n(200/100 İndirim)",
        "category": "KUPON & İNDİRİM",
        "grad_start": (80, 45, 10),
        "grad_end": (190, 120, 30),
        "badge_color": (255, 230, 200)
    },
    {
        "filename": "lisansarena_shell.png",
        "title": "Shell\n100 TL Yakıt Puanı",
        "category": "KUPON & İNDİRİM",
        "grad_start": (80, 45, 10),
        "grad_end": (190, 120, 30),
        "badge_color": (255, 230, 200)
    },
    {
        "filename": "lisansarena_steam.png",
        "title": "Steam Random Key\n(Gold)",
        "category": "TASARIM & YAZILIM",
        "grad_start": (10, 48, 70),
        "grad_end": (25, 120, 160),
        "badge_color": (200, 240, 255)
    },
    {
        "filename": "lisansarena_office365.png",
        "title": "Office 365 Pro\n(1 Yıllık)",
        "category": "TASARIM & YAZILIM",
        "grad_start": (10, 48, 70),
        "grad_end": (25, 120, 160),
        "badge_color": (200, 240, 255)
    }
]

def draw_cover(img_info):
    w, h = 800, 800
    base = Image.new("RGB", (w, h), img_info["grad_start"])
    draw = ImageDraw.Draw(base)
    
    # Draw background gradient
    for y in range(h):
        r = int(img_info["grad_start"][0] + (img_info["grad_end"][0] - img_info["grad_start"][0]) * y / h)
        g = int(img_info["grad_start"][1] + (img_info["grad_end"][1] - img_info["grad_start"][1]) * y / h)
        b = int(img_info["grad_start"][2] + (img_info["grad_end"][2] - img_info["grad_start"][2]) * y / h)
        draw.line((0, y, w, y), fill=(r, g, b))
        
    # Draw translucent glassmorphism container
    card_margin = 85
    draw.rounded_rectangle(
        [(card_margin, card_margin), (w - card_margin, h - card_margin)],
        radius=35,
        fill=(0, 0, 0, 110),
        outline=(255, 255, 255, 30),
        width=3
    )
    
    font_path = "arial.ttf"
    try:
        font_title = ImageFont.truetype(font_path, 42)
        font_brand = ImageFont.truetype(font_path, 25)
        font_sub = ImageFont.truetype(font_path, 21)
        font_badge = ImageFont.truetype(font_path, 17)
    except IOError:
        font_title = ImageFont.load_default()
        font_brand = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        
    # Category badge
    draw.text((w/2, 175), img_info["category"], font=font_badge, fill=img_info["badge_color"], anchor="mm")
    
    # Brand title at top container
    draw.text((w/2, 230), "LISANSARENA", font=font_brand, fill=(255, 255, 255), anchor="mm")
    
    # Draw underline for brand
    draw.line((w/2 - 90, 250, w/2 + 90, 250), fill=(255, 255, 255, 100), width=2)
    
    # Title (multiline support)
    title_lines = img_info["title"].split("\n")
    y_text = 400 - (len(title_lines) - 1) * 30
    for line in title_lines:
        draw.text((w/2, y_text), line, font=font_title, fill=(255, 255, 255), anchor="mm")
        y_text += 65
        
    # Bottom labels
    draw.text((w/2, 595), "ANINDA DİJİTAL TESLİMAT", font=font_sub, fill=(160, 255, 160), anchor="mm")
    draw.text((w/2, 635), "GÜVENLİ ÖDEME | %100 GARANTİLİ", font=font_sub, fill=(225, 225, 225), anchor="mm")
    
    dst_path = os.path.join(static_dir, img_info["filename"])
    base.save(dst_path, "PNG")
    print(f"Generated: {img_info['filename']}")

print("Generating native LisansArena cover images...")
for img in target_images:
    draw_cover(img)
print("Generation finished.")
