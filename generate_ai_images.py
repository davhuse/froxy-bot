import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from create_shopier_listings import products

# Absolute paths to the AI generated backgrounds
BG_PATHS = {
    "AI": r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\bg_ai_1781826501695.png",
    "Entertainment": r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\bg_ent_1781826509410.png",
    "Design": r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\bg_design_1781826518812.png",
    "Numbers": r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\bg_numbers_1781826528379.png",
    "Coupons": r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\bg_coupons_1781826536127.png"
}

OUTPUT_DIR = os.path.join(os.getcwd(), "shopier_ai_images")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_glassmorphism_card(title, category, filename):
    w, h = 800, 800
    
    bg_path = BG_PATHS.get(category, BG_PATHS["Design"])
    try:
        base = Image.open(bg_path).convert("RGBA")
        base = base.resize((w, h), Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"Error loading {bg_path}: {e}")
        base = Image.new("RGBA", (w, h), (30, 30, 30, 255))
        
    # Create the glass pane
    card_margin = 60
    pane_w = w - (card_margin * 2)
    pane_h = h - (card_margin * 2)
    
    # We create a blurred version of the background for the glass effect
    blurred_base = base.filter(ImageFilter.GaussianBlur(radius=15))
    
    # Create a mask for the rounded rectangle
    mask = Image.new("L", (w, h), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle(
        [(card_margin, card_margin), (w - card_margin, h - card_margin)],
        radius=40,
        fill=255
    )
    
    # Composite the blurred background onto the base using the mask
    base.paste(blurred_base, (0, 0), mask=mask)
    
    # Add a semi-transparent dark overlay to the glass pane to make text readable
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    draw_overlay.rounded_rectangle(
        [(card_margin, card_margin), (w - card_margin, h - card_margin)],
        radius=40,
        fill=(10, 10, 15, 140), # Dark translucent fill
        outline=(255, 255, 255, 60), # Bright subtle border
        width=2
    )
    
    # Merge overlay with base
    base = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(base)
    
    # Setup fonts
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 46) # Arial Bold
        font_sub = ImageFont.truetype("arial.ttf", 26)
        font_badge = ImageFont.truetype("arialbd.ttf", 20)
    except IOError:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        
    # Category Translation
    cat_tr = {
        "AI": "YAPAY ZEKA (AI)",
        "Entertainment": "EĞLENCE & MÜZİK",
        "Design": "TASARIM & YAZILIM",
        "Numbers": "ONAYLI NUMARA & MAİL",
        "Coupons": "KUPON & İNDİRİM"
    }
    cat_turkish = cat_tr.get(category, "DİJİTAL ÜRÜN")

    # Draw Category Badge at top
    draw.text((w/2, 160), cat_turkish, font=font_badge, fill=(180, 210, 255, 255), anchor="mm")
    
    # Text Wrapping for Title
    words = title.split()
    lines = []
    current_line = []
    for word in words:
        if len(" ".join(current_line + [word])) * 22 < pane_w - 60:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    y_text = 360 - (len(lines) - 1) * 30
    for line in lines[:4]:
        draw.text((w/2, y_text), line, font=font_title, fill=(255, 255, 255, 255), anchor="mm")
        y_text += 65
        
    # Footer Badges
    draw.text((w/2, 600), "💎 ANINDA DİJİTAL TESLİMAT 💎", font=font_sub, fill=(180, 255, 180, 255), anchor="mm")
    draw.text((w/2, 645), "🛡️ %100 GÜVENLİ VE GARANTİLİ 🛡️", font=font_sub, fill=(220, 220, 220, 255), anchor="mm")
    
    # Convert back to RGB to save as JPG
    final_img = base.convert("RGB")
    final_img.save(filename, "JPEG", quality=95)

if __name__ == "__main__":
    print("Generating Premium AI Glassmorphism Covers...")
    for idx, p in enumerate(products):
        filename = os.path.join(OUTPUT_DIR, f"product_{idx}.jpg")
        create_glassmorphism_card(p["name"], p["category"], filename)
        print(f"Generated: {filename}")
    print("\nAll 49 images generated successfully in 'shopier_ai_images' folder!")
