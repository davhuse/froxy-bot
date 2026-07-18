import os
from PIL import Image, ImageDraw, ImageFont

static_dir = r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\static"

def make_keyvadi_image(src_path, dst_path):
    img = Image.open(src_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    
    # Cover the 'LISANSARENA' text and underline (y=205 to y=255)
    # The background card has fill=(0, 0, 0, 110). We will draw a dark card header block
    draw.rectangle([(280, 210), (744, 255)], fill=(10, 10, 12, 255))
    
    try:
        # Load Arial font
        font = ImageFont.truetype("arial.ttf", 26)
    except Exception:
        font = ImageFont.load_default()
        
    # Draw 'KEYVADI' text
    draw.text((512, 230), "KEYVADI", font=font, fill=(255, 255, 255), anchor="mm")
    
    # Draw underline
    draw.line((512-70, 246, 512+70, 246), fill=(255, 255, 255, 120), width=2)
    
    # Save as PNG
    img.convert("RGB").save(dst_path, "PNG")
    print(f"Successfully generated: {dst_path}")

# Run for both HBO Max and Prime Video
make_keyvadi_image(os.path.join(static_dir, "la_hbo.png"), os.path.join(static_dir, "kv_hbo.png"))
make_keyvadi_image(os.path.join(static_dir, "la_prime.png"), os.path.join(static_dir, "kv_prime.png"))
