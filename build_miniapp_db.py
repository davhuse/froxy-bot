import json
import re
import os

with open('keyvadi_shopier_links.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

def find_image(title):
    t = title.lower()
    if 'gemini' in t:
        return 'assets/google_gemini_mockup.png'
    elif 'grok' in t:
        return 'assets/super_grok_mockup.png'
    elif 'chat gpt' in t or 'chatgpt' in t:
        return 'assets/bg_ai_1781826501695.png'
    elif 'canva' in t:
        return 'assets/canva_pro_mockup_1783808487040.png'
    elif 'adobe' in t:
        return 'assets/adobe_product_mockup_1783808303595.png'
    elif 'capcut' in t:
        return 'assets/capcut_pro_mockup_1783808568631.png'
    elif 'gamma' in t:
        return 'assets/gamma_app_mockup_1783808561382.png'
    elif 'netflix' in t:
        return 'assets/netflix_product_mockup_1783808293526.png'
    elif 'spotify' in t:
        return 'assets/spotify_premium_mockup_1783808941084.png'
    elif 'youtube' in t:
        return 'assets/youtube_premium_mockup_1783808479646.png'
    elif 'prime' in t or 'amazon' in t:
        return 'assets/bg_ent_1781826509410.png'
    elif 'hbo' in t:
        return 'assets/hbo_max_mockup_1783810837183.png'
    elif 'crunchyroll' in t:
        return 'assets/crunchyroll_mockup_1783810843980.png'
    elif 'duolingo' in t:
        return 'assets/duolingo_super_mockup_1783808576605.png'
    elif 'steam' in t:
        return 'assets/steam_game_mockup_1783808536421.png'
    elif 'xbox' in t or 'game pass' in t:
        return 'assets/xbox_gamepass_mockup_1783808518457.png'
    elif 'kaspersky' in t:
        return 'assets/windows_pro_mockup_1783808497788.png'
    elif 'windows' in t:
        return 'assets/windows_pro_mockup_1783808497788.png'
    elif 'office' in t:
        return 'assets/office_365_mockup_1783808510588.png'
    elif 'semrush' in t:
        return 'assets/semrush_pro_mockup_1783808525836.png'
    elif 'trendyol' in t:
        return 'assets/trendyol_yemek_mockup_1783809047496.png'
    elif 'shell' in t:
        return 'assets/shell_puan_mockup_1783809063688.png'
    elif 'discord' in t or 'nitro' in t:
        return 'assets/bg_numbers_1781826528379.png'
    elif 'zula' in t or 'fc26' in t:
        return 'assets/steam_game_mockup_1783808536421.png'
    return 'assets/keyvadi_banner.png'

def get_category(title):
    t = title.lower()
    if any(k in t for k in ['gemini', 'gpt', 'grok', 'ai', 'deepl', 'magnific', 'grammarly', 'perplexity']):
        return 'ai'
    elif any(k in t for k in ['canva', 'adobe', 'capcut', 'gamma', 'tasarim', 'express']):
        return 'design'
    elif any(k in t for k in ['netflix', 'spotify', 'youtube', 'prime', 'hbo', 'crunchyroll', 'scribd', 'duolingo']):
        return 'entertainment'
    elif any(k in t for k in ['steam', 'xbox', 'game pass', 'zula', 'fc26', 'oyun', 'discord']):
        return 'gaming'
    elif any(k in t for k in ['windows', 'office', 'kaspersky', 'lisans', 'semrush', 'key']):
        return 'software'
    elif any(k in t for k in ['trendyol', 'shell', 'kupon', 'yemek', 'market']):
        return 'coupons'
    return 'other'

def get_badge(title):
    t = title.lower()
    if 'ilk kullanım garantili' in t or 'özel profil' in t or 'kendi mailinize' in t or 'kişisel' in t:
        return '✨ Kişisel / Özel'
    elif 'ortak' in t:
        return '👥 Ortak Hesap'
    elif 'random' in t:
        return '🎲 Random Key'
    elif 'anında' in t or '1 aylık' in t or '1 yıl' in t or '3 aylık' in t:
        return '⚡ Hızlı Teslimat'
    return '⭐ Popüler'

def parse_price_num(price_str):
    p = price_str.replace('TL', '').replace('tl', '').strip()
    p = p.replace('.', '').replace(',', '.')
    try:
        return float(p)
    except:
        return 0.0

enriched = []
for p in products:
    price_num = parse_price_num(p.get('price', '0'))
    cat = get_category(p.get('title', ''))
    img = find_image(p.get('title', ''))
    badge = get_badge(p.get('title', ''))
    title = p.get('title', '')
    
    enriched.append({
        'id': str(p.get('id', '')),
        'title': title,
        'price': p.get('price', ''),
        'price_num': price_num,
        'category': cat,
        'image': img,
        'badge': badge,
        'url': p.get('url', ''),
        'description': f"{title} - KeyVadi güvencesiyle 7/24 otomatik anında teslimat ve garanti desteği."
    })

os.makedirs('miniapp', exist_ok=True)
with open('miniapp/products_db.json', 'w', encoding='utf-8') as f:
    json.dump(enriched, f, ensure_ascii=False, indent=2)

print(f'Done! Enriched {len(enriched)} products.')
