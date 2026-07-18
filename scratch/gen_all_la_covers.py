import os
from PIL import Image, ImageDraw, ImageFont

static_dir = r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\static"

products = [
    {"slug": "netflix_4k", "title": "Netflix 4K Ultra HD\n(Kişisel Profil)", "cat": "EĞLENCE & MÜZİK", "g1": (60, 6, 6), "g2": (180, 20, 20)},
    {"slug": "office365", "title": "Microsoft Office 365\n(1 Yıllık Hesap)", "cat": "TASARIM & YAZILIM", "g1": (10, 48, 70), "g2": (25, 120, 160)},
    {"slug": "windows_pro", "title": "Windows 10/11 Pro\nLisans Anahtarı", "cat": "TASARIM & YAZILIM", "g1": (10, 48, 70), "g2": (25, 120, 160)},
    {"slug": "steam_oyun", "title": "Steam İstediğiniz Oyun\n(Ortak Hesap)", "cat": "TASARIM & YAZILIM", "g1": (10, 48, 70), "g2": (25, 120, 160)},
    {"slug": "super_grok_1m", "title": "Super Grok\n(1 Aylık Hesap)", "cat": "YAPAY ZEKA (AI)", "g1": (24, 18, 59), "g2": (89, 56, 172)},
    {"slug": "super_grok_3m", "title": "Super Grok\n(3 Aylık Hesap)", "cat": "YAPAY ZEKA (AI)", "g1": (24, 18, 59), "g2": (89, 56, 172)},
    {"slug": "super_grok_6m", "title": "Super Grok\n(6 Aylık Hesap)", "cat": "YAPAY ZEKA (AI)", "g1": (24, 18, 59), "g2": (89, 56, 172)},
    {"slug": "super_grok_12m", "title": "Super Grok\n(12 Aylık Hesap)", "cat": "YAPAY ZEKA (AI)", "g1": (24, 18, 59), "g2": (89, 56, 172)},
    {"slug": "gamma_ultra", "title": "Gamma Ultra\n(1 Aylık Hesap)", "cat": "YAPAY ZEKA (AI)", "g1": (24, 18, 59), "g2": (89, 56, 172)},
    {"slug": "gamma_pro", "title": "Gamma Pro\n(1 Aylık Hesap)", "cat": "YAPAY ZEKA (AI)", "g1": (24, 18, 59), "g2": (89, 56, 172)},
    {"slug": "gemini_ultra_davet", "title": "Gemini Ultra\n(Davet Linki)", "cat": "YAPAY ZEKA (AI)", "g1": (24, 18, 59), "g2": (89, 56, 172)},
    {"slug": "gemini_ultra_2500", "title": "Gemini Ultra\n(2.5k Kredili Hesap)", "cat": "YAPAY ZEKA (AI)", "g1": (24, 18, 59), "g2": (89, 56, 172)},
    {"slug": "gemini_pro_davet_12m", "title": "Gemini Pro Davet\n(12 Aylık)", "cat": "YAPAY ZEKA (AI)", "g1": (24, 18, 59), "g2": (89, 56, 172)},
    {"slug": "gemini_pro_hesap_12m", "title": "Gemini Pro\nPremium Hesap (12 Aylık)", "cat": "YAPAY ZEKA (AI)", "g1": (24, 18, 59), "g2": (89, 56, 172)},
]

def draw_cover(p):
    w, h = 800, 800
    base = Image.new("RGB", (w, h), p["g1"])
    draw = ImageDraw.Draw(base)
    for y in range(h):
        r = int(p["g1"][0] + (p["g2"][0] - p["g1"][0]) * y / h)
        g = int(p["g1"][1] + (p["g2"][1] - p["g1"][1]) * y / h)
        b = int(p["g1"][2] + (p["g2"][2] - p["g1"][2]) * y / h)
        draw.line((0, y, w, y), fill=(r, g, b))
    draw.rounded_rectangle([(85, 85), (w-85, h-85)], radius=35, fill=(0, 0, 0, 110), outline=(255, 255, 255, 30), width=3)
    try:
        ft = ImageFont.truetype("arial.ttf", 42)
        fb = ImageFont.truetype("arial.ttf", 25)
        fs = ImageFont.truetype("arial.ttf", 21)
        fc = ImageFont.truetype("arial.ttf", 17)
    except:
        ft = fb = fs = fc = ImageFont.load_default()
    draw.text((w/2, 175), p["cat"], font=fc, fill=(200, 220, 255), anchor="mm")
    draw.text((w/2, 230), "LISANSARENA", font=fb, fill=(255, 255, 255), anchor="mm")
    draw.line((w/2-90, 250, w/2+90, 250), fill=(255, 255, 255, 100), width=2)
    lines = p["title"].split("\n")
    y_t = 400 - (len(lines)-1)*30
    for line in lines:
        draw.text((w/2, y_t), line, font=ft, fill=(255, 255, 255), anchor="mm")
        y_t += 65
    draw.text((w/2, 595), "ANINDA DİJİTAL TESLİMAT", font=fs, fill=(160, 255, 160), anchor="mm")
    draw.text((w/2, 635), "GÜVENLİ ÖDEME | %100 GARANTİLİ", font=fs, fill=(225, 225, 225), anchor="mm")
    dst = os.path.join(static_dir, f"la_{p['slug']}.png")
    base.save(dst, "PNG")
    print(f"Generated: la_{p['slug']}.png")

for p in products:
    draw_cover(p)
print(f"Done! {len(products)} images generated.")
