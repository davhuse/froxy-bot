# -*- coding: utf-8 -*-
import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.stdout.reconfigure(encoding='utf-8')

PRODUCTS = [
    {
        "filename": "card_clean_ssport.jpg",
        "brand_badge": "KEYVADI | SPOR & CANLI YAYIN",
        "title": "S SPORT PLUS",
        "subtitle": "1 Aylık Premium Lisans",
        "tagline": "Premier League • La Liga • Serie A • EuroLeague • NBA • F1",
        "highlight": "Canlı Maçlar & Tekrar İzle • Full HD Yayın",
        "price": "70.00 ₺",
        "colors": {
            "bg_top": (10, 15, 35),
            "bg_bottom": (18, 25, 55),
            "glow": (0, 180, 255),
            "accent": (255, 60, 40),
            "border": (50, 120, 220)
        }
    },
    {
        "filename": "card_clean_yemeksepeti.jpg",
        "brand_badge": "KEYVADI | YEMEK & KUPON",
        "title": "YEMEKSEPETİ",
        "subtitle": "450₺'ye 350₺ İndirim Kodu",
        "tagline": "Tüm Restoranlarda Geçerli • Anında 350 TL İndirim",
        "highlight": "Sepette Anında Düşer • Hızlı Teslimat Kodu",
        "price": "60.00 ₺",
        "colors": {
            "bg_top": (40, 10, 25),
            "bg_bottom": (70, 15, 40),
            "glow": (255, 30, 90),
            "accent": (255, 200, 50),
            "border": (255, 70, 120)
        }
    },
    {
        "filename": "card_clean_turna.jpg",
        "brand_badge": "KEYVADI | SEYAHAT & UÇAK",
        "title": "TURNA.COM",
        "subtitle": "600 TL Uçak Bileti Kuponu",
        "tagline": "Yurt İçi & Yurt Dışı Her Yöne Geçerli 600 TL İndirim",
        "highlight": "Tek Yön & Gidiş-Dönüş Biletlerde Geçerli",
        "price": "70.00 ₺",
        "colors": {
            "bg_top": (35, 10, 15),
            "bg_bottom": (60, 15, 20),
            "glow": (230, 0, 40),
            "accent": (255, 220, 80),
            "border": (220, 50, 60)
        }
    },
    {
        "filename": "card_clean_tiklagelsin.jpg",
        "brand_badge": "KEYVADI | RESTORAN & YEMEK",
        "title": "TIKLA GELSİN",
        "subtitle": "400₺'ye 200₺ Yemek Kuponu",
        "tagline": "Burger King • Popeyes • Arby's • Usta Dönerci • Sbarro",
        "highlight": "Gel Al ve Sana Gelsin Siparişlerinde 200 TL İndirim",
        "price": "50.00 ₺",
        "colors": {
            "bg_top": (30, 15, 10),
            "bg_bottom": (55, 25, 12),
            "glow": (255, 110, 20),
            "accent": (255, 215, 0),
            "border": (240, 130, 40)
        }
    }
]

def get_font(size, bold=False):
    font_paths = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_card(p):
    W, H = 1024, 1024
    im = Image.new("RGB", (W, H), p["colors"]["bg_top"])
    
    # Background gradient
    for y in range(H):
        r1, g1, b1 = p["colors"]["bg_top"]
        r2, g2, b2 = p["colors"]["bg_bottom"]
        factor = y / H
        r = int(r1 + (r2 - r1) * factor)
        g = int(g1 + (g2 - g1) * factor)
        b = int(b1 + (b2 - b1) * factor)
        for x in range(W):
            pass # optimize via line drawing
    
    # Fast gradient drawing
    draw = ImageDraw.Draw(im)
    r1, g1, b1 = p["colors"]["bg_top"]
    r2, g2, b2 = p["colors"]["bg_bottom"]
    for y in range(H):
        factor = y / H
        r = int(r1 + (r2 - r1) * factor)
        g = int(g1 + (g2 - g1) * factor)
        b = int(b1 + (b2 - b1) * factor)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
        
    # Glow circle in center
    glow_im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_im)
    glow_color = p["colors"]["glow"] + (40,)
    glow_draw.ellipse([(150, 150), (W - 150, H - 200)], fill=glow_color)
    glow_im = glow_im.filter(ImageFilter.GaussianBlur(80))
    im.paste(glow_im, (0, 0), glow_im)

    # Main Card Container (Glassmorphism effect)
    margin = 70
    card_box = [(margin, margin), (W - margin, H - margin)]
    
    # Overlay card
    card_ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_ov)
    card_draw.rounded_rectangle(card_box, radius=40, fill=(15, 18, 30, 200), outline=p["colors"]["border"], width=3)
    im.paste(card_ov, (0, 0), card_ov)
    
    draw = ImageDraw.Draw(im)
    
    # 1. Top Brand Pill
    f_badge = get_font(26, bold=True)
    pill_text = p["brand_badge"]
    pill_w = draw.textlength(pill_text, font=f_badge) + 40
    pill_h = 44
    pill_x = (W - pill_w) / 2
    pill_y = margin + 50
    draw.rounded_rectangle([(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)], radius=22, fill=(25, 30, 50), outline=p["colors"]["border"], width=2)
    draw.text((pill_x + 20, pill_y + 8), pill_text, font=f_badge, fill=p["colors"]["accent"])
    
    # 2. Main Title
    f_title = get_font(68, bold=True)
    title_text = p["title"]
    tw = draw.textlength(title_text, font=f_title)
    draw.text(((W - tw) / 2, pill_y + 90), title_text, font=f_title, fill=(255, 255, 255))
    
    # 3. Subtitle / Discount
    f_sub = get_font(44, bold=True)
    sub_text = p["subtitle"]
    sw = draw.textlength(sub_text, font=f_sub)
    draw.text(((W - sw) / 2, pill_y + 185), sub_text, font=f_sub, fill=p["colors"]["glow"])
    
    # Divider line with accent
    div_y = pill_y + 260
    div_w = 400
    draw.line([((W - div_w) / 2, div_y), ((W + div_w) / 2, div_y)], fill=p["colors"]["border"], width=2)
    
    # 4. Features & Highlights Box
    feat_box_y = div_y + 45
    feat_box_h = 220
    draw.rounded_rectangle([(margin + 50, feat_box_y), (W - margin - 50, feat_box_y + feat_box_h)], radius=24, fill=(10, 14, 25), outline=(60, 70, 95), width=2)
    
    f_high = get_font(32, bold=True)
    hw = draw.textlength(p["highlight"], font=f_high)
    draw.text(((W - hw) / 2, feat_box_y + 35), p["highlight"], font=f_high, fill=(255, 255, 255))
    
    f_tag = get_font(26, bold=False)
    tag_w = draw.textlength(p["tagline"], font=f_tag)
    draw.text(((W - tag_w) / 2, feat_box_y + 95), p["tagline"], font=f_tag, fill=(180, 195, 215))
    
    f_guar = get_font(24, bold=True)
    guar_text = "✓ 7/24 Anında Teslimat  •  ✓ Süre Boyunca Birebir Telafi Garantisi"
    gw = draw.textlength(guar_text, font=f_guar)
    draw.text(((W - gw) / 2, feat_box_y + 155), guar_text, font=f_guar, fill=(100, 230, 150))
    
    # 5. Price & Buy CTA Box
    price_box_y = feat_box_y + feat_box_h + 40
    price_box_h = 130
    price_w = 560
    px = (W - price_w) / 2
    draw.rounded_rectangle([(px, price_box_y), (px + price_w, price_box_y + price_box_h)], radius=30, fill=p["colors"]["accent"], outline=(255, 255, 255), width=2)
    
    f_price_label = get_font(24, bold=True)
    draw.text((px + 45, price_box_y + 24), "GÜNCEL FİYAT:", font=f_price_label, fill=(20, 20, 20))
    
    f_price_val = get_font(56, bold=True)
    draw.text((px + 40, price_box_y + 50), p["price"], font=f_price_val, fill=(10, 10, 10))
    
    f_shopier = get_font(28, bold=True)
    sh_text = "Shopier Güvencesi"
    draw.text((px + price_w - 260, price_box_y + 35), sh_text, font=f_shopier, fill=(10, 10, 10))
    f_shopier_sub = get_font(20, bold=False)
    draw.text((px + price_w - 260, price_box_y + 75), "3D Secure • Kredi Kartı / Havale", font=f_shopier_sub, fill=(40, 40, 40))
    
    # 6. Bottom footer info
    f_bot = get_font(22, bold=False)
    bot_info = "Sipariş & Bilgi: @KeyvadiDestek  |  Otomatik Bot: @KeyVadiSatisBot"
    bw = draw.textlength(bot_info, font=f_bot)
    draw.text(((W - bw) / 2, H - margin - 45), bot_info, font=f_bot, fill=(160, 175, 200))
    
    # Save image
    out_paths = [
        os.path.join("miniapp", "assets", "products", p["filename"]),
        os.path.join("static", p["filename"])
    ]
    for out in out_paths:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        im.save(out, "JPEG", quality=95)
        print(f"Saved: {out}")

for prod in PRODUCTS:
    draw_card(prod)

print("All 4 product cards generated successfully!")
