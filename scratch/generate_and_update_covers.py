import urllib.request
import urllib.error
import json
import ssl
import os
import sys
from PIL import Image, ImageDraw, ImageFont

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 1. Generate the branded cover images
def create_canva_teacher_image(badge_text, filename, c1, c2):
    w, h = 800, 800
    base = Image.new("RGB", (w, h), c1)
    draw = ImageDraw.Draw(base)
    
    # Draw gradient
    for y in range(h):
        r = int(c1[0] + (c2[0] - c1[0]) * y / h)
        g = int(c1[1] + (c2[1] - c1[1]) * y / h)
        b = int(c1[2] + (c2[2] - c1[2]) * y / h)
        draw.line((0, y, w, y), fill=(r, g, b))
        
    # Draw card overlay
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
        
    draw.text((w/2, 170), badge_text, font=font_badge, fill=(200, 220, 255), anchor="mm")
    
    # Draw main text lines
    draw.text((w/2, 330), "Canva Pro Öğretmen", font=font_title, fill=(255, 255, 255), anchor="mm")
    draw.text((w/2, 390), "(1 Yıllık Üyelik)", font=font_title, fill=(255, 255, 255), anchor="mm")
    
    draw.text((w/2, 595), "ÖĞRENCİ EKLEME YETKİSİ", font=font_sub, fill=(160, 255, 160), anchor="mm")
    draw.text((w/2, 635), "KENDİ MAİLİNİZE TANIMLI", font=font_sub, fill=(225, 225, 225), anchor="mm")
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    base.save(filename, "PNG")
    print(f"Generated image: {filename}")

# Generate KeyVadi image (Deep Purple gradient)
create_canva_teacher_image(
    badge_text="KEYVADİ DİJİTAL",
    filename="static/keyvadi_canva_teacher.png",
    c1=(25, 10, 50),
    c2=(75, 20, 120)
)

# Generate LisansArena image (Teal / Blue gradient)
create_canva_teacher_image(
    badge_text="LİSANSARENA",
    filename="static/la_canva_teacher.png",
    c1=(10, 45, 65),
    c2=(25, 110, 150)
)

# 2. Update Shopier store cover images via API
tokens_path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\saved_shopier_tokens.json"
if not os.path.exists(tokens_path):
    print("Error: saved_shopier_tokens.json not found!")
    sys.exit(1)
    
with open(tokens_path, "r", encoding="utf-8") as f:
    tokens = json.load(f)
    
token_kv = tokens.get("keyvadi")
token_la = tokens.get("lisansarena")

def update_cover(token, pid, filename, store_name):
    url = f"https://api.shopier.com/v1/products/{pid}"
    payload = {
        "media": [
            {
                "type": "image",
                "url": f"https://veridia-bot.onrender.com/static/{filename}",
                "placement": 1
            }
        ]
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    print(f"Updating ID {pid} on {store_name} to use {filename}...")
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            print("  [SUCCESS] Updated Shopier cover!")
    except urllib.error.HTTPError as e:
        print(f"  [FAILED] HTTP Error {e.code}: {e.reason}")
        try:
            print("  Response Body:", e.read().decode("utf-8"))
        except:
            pass
    except Exception as e:
        print(f"  [FAILED] Error: {e}")

# KeyVadi Canva Pro Teacher ID: 49078921
update_cover(token_kv, "49078921", "keyvadi_canva_teacher.png", "KeyVadi")

# LisansArena Canva Pro Teacher ID: 49078922
update_cover(token_la, "49078922", "la_canva_teacher.png", "LisansArena")

# 3. Update the media URLs in lisansarena_shopier_links.json
links_la_path = "lisansarena_shopier_links.json"
if os.path.exists(links_la_path):
    with open(links_la_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        if item.get("id") == "49078922":
            item["media"] = [
                {
                    "id": "1",
                    "type": "image",
                    "url": "https://veridia-bot.onrender.com/static/la_canva_teacher.png",
                    "placement": 1
                }
            ]
            print("Updated la_canva_teacher.png media URL in lisansarena_shopier_links.json")
            break
    with open(links_la_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
