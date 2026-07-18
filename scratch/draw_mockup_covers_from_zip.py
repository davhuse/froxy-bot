import os
import zipfile
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter

zip_path = r"C:\Users\habil\Downloads\download.zip"
extract_dir = r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\scratch\extracted_gorseller"
static_dir = r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\static"

os.makedirs(extract_dir, exist_ok=True)

# 1. Extract the zip file
print(f"Extracting {zip_path}...")
try:
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_dir)
    print("Extraction successful!")
except Exception as e:
    print(f"Extraction failed: {e}")
    exit(1)

# List of files we need to process
products_to_gen = [
    # EĞLENCE & MÜZİK
    {
        "slug": "netflix_4k",
        "zip_file": "Netflix_logo_on_screen_202607151802.jpeg",
        "title": "Netflix 4K Ultra HD\n(Kişisel Profil)",
        "cat": "EĞLENCE & MÜZİK",
        "kv_slug": "netflix_kisisel" # Wait, KeyVadi Netflix is keyvadi_netflix_kisisel.png? Or let's save both!
    },
    {
        "slug": "hbo",
        "zip_file": "HBO_Max_logo_on_screen_202607151802.jpeg",
        "title": "HBO Max Premium\n(1 Aylık Profil)",
        "cat": "EĞLENCE & MÜZİK"
    },
    {
        "slug": "prime",
        "zip_file": "Prime_Video_logo_on_screen_202607151802.jpeg",
        "title": "Prime Video\n(Özel Profil)",
        "cat": "EĞLENCE & MÜZİK",
        "is_prime_video": True # We'll handle Ortak and Özel
    },
    {
        "slug": "youtube",
        "zip_file": "YouTube_Premium_3D_mockup_202607151802.jpeg",
        "title": "YouTube Premium\n(3 Aylık Kod)",
        "cat": "EĞLENCE & MÜZİK"
    },
    {
        "slug": "spotify",
        "zip_file": "Spotify_Premium_3D_mockup_202607151802.jpeg",
        "title": "Spotify Premium\n(4 Aylık Kod)",
        "cat": "EĞLENCE & MÜZİK"
    },
    {
        "slug": "crunchyroll",
        "zip_file": "Crunchyroll_Premium_3D_mockup_202607151802.jpeg",
        "title": "Crunchyroll Premium\n(1 Aylık Üyelik)",
        "cat": "EĞLENCE & MÜZİK",
        "is_crunchyroll": True
    },
    
    # YAPAY ZEKA (AI)
    {
        "slug": "perplexity_pro",
        "zip_file": "Perplexity_Pro_AI_product_mockup_202607151802.jpeg",
        "title": "Perplexity Pro\n(1 Aylık Hesap)",
        "cat": "YAPAY ZEKA (AI)"
    },
    {
        "slug": "deepl",
        "zip_file": "DeepL_AI_Translator_Pro_card_202607151802.jpeg",
        "title": "DeepL AI Translator\n(1 Aylık Üyelik)",
        "cat": "YAPAY ZEKA (AI)",
        "is_deepl": True
    },
    {
        "slug": "magnific_ai",
        "zip_file": "AI_brain_logo_on_screen_202607151802.jpeg",
        "title": "Magnific AI\n(Business Ortak Hesap)",
        "cat": "YAPAY ZEKA (AI)"
    },
    {
        "slug": "gemini_pro",
        "zip_file": "Gemini_Pro_3D_product_mockup_202607151802.jpeg",
        "title": "Gemini Pro\nPremium Hesap (12 Aylık)",
        "cat": "YAPAY ZEKA (AI)",
        "is_gemini": True
    },
    {
        "slug": "super_grok",
        "zip_file": "Super_Grok_Account_3D_mockup_202607151802.jpeg",
        "title": "Super Grok\n(1 Aylık Hesap)",
        "cat": "YAPAY ZEKA (AI)",
        "is_grok": True
    },
    {
        "slug": "gamma",
        "zip_file": "Gamma_Pro_Ultra_logo_mockup_202607151802.jpeg",
        "title": "Gamma Premium\n(1 Aylık Hesap)",
        "cat": "YAPAY ZEKA (AI)",
        "is_gamma": True
    },
    
    # TASARIM & YAZILIM
    {
        "slug": "canva",
        "zip_file": "Teal_Canva_logo_3D_mockup_202607151802.jpeg",
        "title": "Canva Pro\n(1 Yıllık Yetki)",
        "cat": "TASARIM & YAZILIM"
    },
    {
        "slug": "office365",
        "zip_file": "Microsoft_Office_365_logo_mockup_202607151802.jpeg",
        "title": "Microsoft Office 365\n(1 Yıllık Hesap)",
        "cat": "TASARIM & YAZILIM"
    },
    {
        "slug": "windows_pro",
        "zip_file": "Windows_10_11_Pro_Lisans_Anahtar__202607151802.jpeg", # Python character correction
        "title": "Windows 10/11 Pro\nLisans Anahtarı",
        "cat": "TASARIM & YAZILIM"
    },
    {
        "slug": "xbox_gamepass",
        "zip_file": "Xbox_Game_Pass_3D_mockup_202607151802.jpeg",
        "title": "Xbox Game Pass\n(3 Aylık Ortak)",
        "cat": "TASARIM & YAZILIM"
    },
    {
        "slug": "scribd",
        "zip_file": "Scribd_Premium_3D_mockup_202607151802.jpeg",
        "title": "Scribd Premium\n(1 Aylık Üyelik)",
        "cat": "TASARIM & YAZILIM",
        "is_scribd": True
    },
    {
        "slug": "grammarly",
        "zip_file": "Grammarly_Pro_3D_mockup_202607151802.jpeg",
        "title": "Grammarly Pro\n(Premium Üyelik)",
        "cat": "TASARIM & YAZILIM",
        "is_grammarly": True
    },
    
    # KUPON & İNDİRİM
    {
        "slug": "trendyol_yemek",
        "zip_file": "Trendyol_Go_discount_coupon_mockup_202607151802.jpeg",
        "title": "Trendyol Go Yemek\n(700/250 İndirim)",
        "cat": "KUPON & İNDİRİM"
    },
    {
        "slug": "trendyol_market",
        "zip_file": "Trendyol_Go_discount_coupon_mockup_202607151802.jpeg",
        "title": "Trendyol Go Market\n(900/250 İndirim)",
        "cat": "KUPON & İNDİRİM"
    },
    {
        "slug": "shell",
        "zip_file": "Shell_Gas_Station_Reward_Card_202607151802.jpeg",
        "title": "Shell\n75 TL Akaryakıt Puanı",
        "cat": "KUPON & İNDİRİM"
    },
    {
        "slug": "telegram_account",
        "zip_file": "Telegram_paper_plane_logo_mockup_202607151802.jpeg",
        "title": "Eski Tarihli\nTelegram Hesabı",
        "cat": "LİSANS & HESAP"
    }
]

def draw_mockup(bg_img, store_name, title, category, dst_path):
    w, h = 800, 800
    base = bg_img.resize((w, h), Image.Resampling.LANCZOS).convert("RGBA")
    
    # Blurred glass pane background
    blurred = base.filter(ImageFilter.GaussianBlur(radius=15))
    
    # Card borders
    card_margin = 85
    mask = Image.new("L", (w, h), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle(
        [(card_margin, card_margin), (w - card_margin, h - card_margin)],
        radius=35,
        fill=255
    )
    
    base.paste(blurred, (0, 0), mask=mask)
    
    # Glass effect overlay
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    draw_overlay.rounded_rectangle(
        [(card_margin, card_margin), (w - card_margin, h - card_margin)],
        radius=35,
        fill=(10, 10, 15, 120),
        outline=(255, 255, 255, 30),
        width=3
    )
    
    base = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(base)
    
    # Fonts
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 42)
        font_sub = ImageFont.truetype("arial.ttf", 23)
        font_badge = ImageFont.truetype("arialbd.ttf", 25)
        font_cat = ImageFont.truetype("arial.ttf", 17)
    except Exception:
        font_title = font_sub = font_badge = font_cat = ImageFont.load_default()
        
    # Draw Category
    draw.text((w/2, 175), category, font=font_cat, fill=(180, 210, 255), anchor="mm")
    
    # Draw Store Title (Watermark)
    draw.text((w/2, 230), store_name, font=font_badge, fill=(255, 255, 255), anchor="mm")
    draw.line((w/2-75, 250, w/2+75, 250), fill=(255, 255, 255, 100), width=2)
    
    # Draw Main Title
    lines = title.split("\n")
    y_t = 400 - (len(lines)-1)*30
    for line in lines:
        draw.text((w/2, y_t), line, font=font_title, fill=(255, 255, 255), anchor="mm")
        y_t += 65
        
    # Draw Subtitles
    draw.text((w/2, 595), "ANINDA DİJİTAL TESLİMAT", font=font_sub, fill=(160, 255, 160), anchor="mm")
    draw.text((w/2, 635), "GÜVENLİ ÖDEME | %100 GARANTİLİ", font=font_sub, fill=(225, 225, 225), anchor="mm")
    
    base.convert("RGB").save(dst_path, "PNG")
    print(f"Generated: {dst_path}")

# Run generation
print("\n--- Starting Image Generation ---")
for p in products_to_gen:
    zip_img_path = os.path.join(extract_dir, p["zip_file"])
    
    # Python character fallback check
    if "Windows_10" in p["zip_file"]:
        # Look for it inside Windows_10 subdirectory
        win_dir = os.path.join(extract_dir, "Windows_10")
        if os.path.isdir(win_dir):
            for fn in os.listdir(win_dir):
                if fn.startswith("11_Pro"):
                    zip_img_path = os.path.join(win_dir, fn)
                    break
                
    if not os.path.exists(zip_img_path) or os.path.isdir(zip_img_path):
        print(f"Warning: Background file not found or is a directory: {zip_img_path}")
        continue
        
    bg_img = Image.open(zip_img_path)
    
    # 1. GENERATE FOR LISANSARENA (la_[slug].png and lisansarena_[slug].png)
    # Special title / slugs handling
    titles_to_la = [(p["title"], f"la_{p['slug']}.png")]
    if p.get("is_prime_video"):
        titles_to_la = [
            ("Prime Video\n(Özel Profil)", "la_prime.png"),
            ("Prime Video\n(Ortak Profil)", "la_prime.png") # Same cover or both
        ]
    elif p.get("is_crunchyroll"):
        titles_to_la = [
            ("Crunchyroll\n(Özel Profil)", "lisansarena_crunchyroll_ozel.png"),
            ("Crunchyroll\n(Ortak Hesap)", "lisansarena_crunchyroll_ortak.png")
        ]
    elif p.get("is_deepl"):
        titles_to_la = [
            ("DeepL AI\n(Kişisel Hesap)", "lisansarena_deepl_kisisel.png"),
            ("DeepL AI\n(Ortak Hesap)", "lisansarena_deepl_ortak.png")
        ]
    elif p.get("is_scribd"):
        titles_to_la = [
            ("Scribd\n(Kişisel Hesap)", "lisansarena_scribd_kisisel.png"),
            ("Scribd\n(Ortak Hesap)", "lisansarena_scribd_ortak.png")
        ]
    elif p.get("is_grammarly"):
        titles_to_la = [
            ("Grammarly Pro\n(Haftalık Davet)", "lisansarena_grammarly_haftalik.png"),
            ("Grammarly Pro\n(Ortak Hesap)", "lisansarena_grammarly_ortak.png")
        ]
    elif p.get("is_grok"):
        titles_to_la = [
            ("Super Grok\n(1 Aylık Hesap)", "la_super_grok_1m.png"),
            ("Super Grok\n(3 Aylık Hesap)", "la_super_grok_3m.png"),
            ("Super Grok\n(6 Aylık Hesap)", "la_super_grok_6m.png"),
            ("Super Grok\n(12 Aylık Hesap)", "la_super_grok_12m.png")
        ]
    elif p.get("is_gamma"):
        titles_to_la = [
            ("Gamma Pro\n(1 Aylık Hesap)", "la_gamma_pro.png"),
            ("Gamma Ultra\n(1 Aylık Hesap)", "la_gamma_ultra.png")
        ]
    elif p.get("is_gemini"):
        titles_to_la = [
            ("Gemini Pro Davet\n(12 Aylık)", "la_gemini_pro_davet_12m.png"),
            ("Gemini Pro\nPremium Hesap (12 Aylık)", "la_gemini_pro_hesap_12m.png"),
            ("Gemini Ultra\n(Davet Linki)", "la_gemini_ultra_davet.png"),
            ("Gemini Ultra\n(2.5k Kredili)", "la_gemini_ultra_2500.png")
        ]
    elif p["slug"] == "office365":
        titles_to_la = [(p["title"], "la_office365.png"), (p["title"], "lisansarena_office365.png")]
    elif p["slug"] == "windows_pro":
        titles_to_la = [(p["title"], "la_windows_pro.png")]
    elif p["slug"] == "shell":
        titles_to_la = [(p["title"], "la_shell.png"), (p["title"], "lisansarena_shell.png")]
    elif p["slug"] == "telegram_account":
        titles_to_la = [(p["title"], "lisansarena_telegram_account.png")]
    elif p["slug"] == "hbo":
        titles_to_la = [(p["title"], "la_hbo.png")]
    elif p["slug"] == "netflix_4k":
        titles_to_la = [(p["title"], "la_netflix_4k.png")]
    
    for t_str, fn in titles_to_la:
        dst = os.path.join(static_dir, fn)
        draw_mockup(bg_img, "LISANSARENA", t_str, p["cat"], dst)
        
    # 2. GENERATE FOR KEYVADI (keyvadi_[slug].png and kv_[slug].png)
    titles_to_kv = [(p["title"], f"keyvadi_{p['slug']}.png")]
    if p.get("is_prime_video"):
        titles_to_kv = [
            ("Prime Video\n(Özel Profil)", "kv_prime.png"),
            ("Prime Video\n(Ortak Profil)", "kv_prime.png")
        ]
    elif p.get("is_crunchyroll"):
        titles_to_kv = [
            ("Crunchyroll\n(Özel Profil)", "keyvadi_crunchyroll_ozel.png"),
            ("Crunchyroll\n(Ortak Hesap)", "keyvadi_crunchyroll_ortak.png")
        ]
    elif p.get("is_deepl"):
        titles_to_kv = [
            ("DeepL AI\n(Kişisel Hesap)", "keyvadi_deepl_kisisel.png"),
            ("DeepL AI\n(Ortak Hesap)", "keyvadi_deepl_ortak.png")
        ]
    elif p.get("is_scribd"):
        titles_to_kv = [
            ("Scribd\n(Kişisel Hesap)", "keyvadi_scribd_kisisel.png"),
            ("Scribd\n(Ortak Hesap)", "keyvadi_scribd_ortak.png")
        ]
    elif p.get("is_grammarly"):
        titles_to_kv = [
            ("Grammarly Pro\n(Haftalık Davet)", "keyvadi_grammarly_haftalik.png"),
            ("Grammarly Pro\n(Ortak Hesap)", "keyvadi_grammarly_ortak.png")
        ]
    elif p["slug"] == "hbo":
        titles_to_kv = [(p["title"], "kv_hbo.png")]
    elif p["slug"] == "magnific_ai":
        titles_to_kv = [(p["title"], "keyvadi_magnific_ai.png")]
    elif p["slug"] == "perplexity_pro":
        titles_to_kv = [(p["title"], "keyvadi_perplexity_pro.png")]
    elif p["slug"] == "telegram_account":
        titles_to_kv = [(p["title"], "keyvadi_telegram_account.png")]
    else:
        # Fallback keyvadi names
        titles_to_kv = [(p["title"], f"keyvadi_{p['slug']}.png")]
        
    for t_str, fn in titles_to_kv:
        dst = os.path.join(static_dir, fn)
        draw_mockup(bg_img, "KEYVADI", t_str, p["cat"], dst)

print("\nAll covers generated successfully!")
