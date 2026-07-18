import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BG_KEYVADI = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\bg_keyvadi_1784412019131.png"
BG_LISANSARENA = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\bg_lisansarena_1784412030563.png"
OUTPUT_DIR = os.path.join(os.getcwd(), "static")

products = [
    ("Steam 200 Dolar Random Key", "30.00 TL", "steam_random"),
    ("Netflix 4K UHD Ortak Profil", "39.99 TL", "netflix_4k"),
    ("Zula Random Hesap", "5.00 TL", "zula_random"),
    ("FC26 + Online Her Şeyi Değişen Hesap", "299.99 TL", "fc26_hesap")
]

def create_card(title, price, filename, store):
    w, h = 1080, 1080
    
    bg_path = BG_KEYVADI if store == "KeyVadi" else BG_LISANSARENA
    try:
        base = Image.open(bg_path).convert("RGBA")
        base = base.resize((w, h), Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"Error loading {bg_path}: {e}")
        base = Image.new("RGBA", (w, h), (30, 30, 30, 255))
        
    card_margin = 80
    pane_w = w - (card_margin * 2)
    pane_h = h - (card_margin * 2)
    
    blurred_base = base.filter(ImageFilter.GaussianBlur(radius=20))
    
    mask = Image.new("L", (w, h), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle(
        [(card_margin, card_margin), (w - card_margin, h - card_margin)],
        radius=50,
        fill=255
    )
    
    base.paste(blurred_base, (0, 0), mask=mask)
    
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    
    # Store specific styles
    if store == "KeyVadi":
        fill_color = (15, 10, 30, 150)
        outline_color = (100, 200, 255, 100)
        badge_color = (150, 200, 255, 255)
    else:
        fill_color = (25, 5, 5, 160)
        outline_color = (255, 100, 100, 100)
        badge_color = (255, 180, 180, 255)

    draw_overlay.rounded_rectangle(
        [(card_margin, card_margin), (w - card_margin, h - card_margin)],
        radius=50,
        fill=fill_color,
        outline=outline_color,
        width=3
    )
    
    base = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(base)
    
    try:
        font_store = ImageFont.truetype("arialbd.ttf", 45)
        font_title = ImageFont.truetype("arialbd.ttf", 65)
        font_price = ImageFont.truetype("arialbd.ttf", 55)
        font_sub = ImageFont.truetype("arial.ttf", 30)
    except IOError:
        font_store = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_price = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        
    draw.text((w/2, 180), store.upper(), font=font_store, fill=badge_color, anchor="mm")
    
    # Text Wrapping for Title
    words = title.split()
    lines = []
    current_line = []
    for word in words:
        if len(" ".join(current_line + [word])) * 30 < pane_w - 100:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    y_text = 420 - (len(lines) - 1) * 40
    for line in lines[:4]:
        draw.text((w/2, y_text), line, font=font_title, fill=(255, 255, 255, 255), anchor="mm")
        y_text += 85
        
    # Price
    draw.text((w/2, 700), price, font=font_price, fill=(255, 215, 0, 255), anchor="mm")

    # Footer
    draw.text((w/2, 850), "💎 ANINDA OTOMATİK TESLİMAT 💎", font=font_sub, fill=(180, 255, 180, 255), anchor="mm")
    draw.text((w/2, 910), "🛡️ %100 GÜVENLİ ALIŞVERİŞ 🛡️", font=font_sub, fill=(220, 220, 220, 255), anchor="mm")
    
    final_img = base.convert("RGB")
    final_img.save(filename, "PNG")

if __name__ == "__main__":
    for title, price, slug in products:
        create_card(title, price, os.path.join(OUTPUT_DIR, f"keyvadi_{slug}.png"), "KeyVadi")
        create_card(title, price, os.path.join(OUTPUT_DIR, f"lisansarena_{slug}.png"), "LisansArena")
    print("Generated all 8 product images successfully!")
