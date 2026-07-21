import json, os

# 1. Mesaj dosyalari kontrolu
print('=== MESAJ DOSYALARI ===')
for brand in ['keyvadi', 'lisansarena']:
    for i in range(1, 7):
        f = f'messages/{brand}_{i}.txt'
        if os.path.exists(f):
            with open(f, 'r', encoding='utf-8') as fh:
                content = fh.read()
            lines = content.strip().split('\n')
            has_bot = False
            if brand == 'keyvadi' and '@KeyVadiSatisBot' in content:
                has_bot = True
            if brand == 'lisansarena' and '@LisansArenaBot' in content:
                has_bot = True
            bot_status = "BOT_OK" if has_bot else "BOT_EKSIK!"
            print(f'  OK {f} ({len(content)} byte, {len(lines)} satir) [{bot_status}]')
        else:
            print(f'  EKSIK {f}')

# 2. Shopier JSON kontrolu
print('\n=== SHOPIER JSON DOSYALARI ===')
for f in ['keyvadi_shopier_links.json', 'lisansarena_shopier_links.json']:
    if os.path.exists(f):
        with open(f, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        print(f'  OK {f} ({len(data)} urun)')
        for item in data[:3]:
            title = item.get('title', 'N/A')
            url = item.get('url', 'N/A')
            print(f'    - {title}: {url}')
    else:
        print(f'  EKSIK {f}')

# 3. Bot config kontrolu
print('\n=== BOT CONFIG ===')
with open('bot_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)
print(f'  KeyVadi Bot Token: {cfg.get("bot_token", "YOK")[:20]}...')
print(f'  Froxy Bot Token: {cfg.get("froxy_bot_token", "YOK")[:20]}...')
print(f'  LisansArena Bot Token: {cfg.get("lisansarena_bot_token", "YOK")[:20]}...')
print(f'  Admin ID: {cfg.get("admin_id", "YOK")}')
print(f'  Ad Bot Running: {cfg.get("ad_bot_running", "YOK")}')
print(f'  Froxy Bot Running: {cfg.get("froxy_bot_running", "YOK")}')
print(f'  LisansArena Bot Running: {cfg.get("lisansarena_bot_running", "YOK")}')
print(f'  Send Images: {cfg.get("send_images", "YOK")}')
print(f'  Cooldown Hours: {cfg.get("group_cooldown_hours", "YOK")}')
print(f'  Sleep Min/Max: {cfg.get("ad_sleep_min", "YOK")}/{cfg.get("ad_sleep_max", "YOK")}')

# Hesap session kontrolu
s1 = cfg.get('ad_string_session', '')
s2 = cfg.get('ad_string_session2', cfg.get('ad_string_session_2', ''))
s3 = cfg.get('ad_string_session3', cfg.get('ad_string_session_3', ''))
print('\n=== HESAP SESSION KONTROL ===')
h1 = f'VAR ({len(s1)} char)' if s1 else 'BOS/YOK'
h2 = f'VAR ({len(s2)} char)' if s2 else 'BOS/YOK'
h3 = f'VAR ({len(s3)} char)' if s3 else 'BOS/YOK'
print(f'  Hesap #1 Session: {h1}')
print(f'  Hesap #2 Session: {h2}')
print(f'  Hesap #3 Session: {h3}')

# 4. Shopier config linkleri
shopier_links = cfg.get('shopier_links', {})
print(f'\n=== SHOPIER CONFIG LINKLERI ({len(shopier_links)} adet) ===')
for key, url in list(shopier_links.items())[:5]:
    print(f'  {key}: {url}')
if len(shopier_links) > 5:
    print(f'  ... ve {len(shopier_links) - 5} adet daha')

# 5. Grup listesi kontrolu
print('\n=== GRUP LISTESI ===')
with open('scraped_groups.txt', 'r', encoding='utf-8') as f:
    scraped = [line.strip() for line in f if line.strip()]
with open('auto_groups.txt', 'r', encoding='utf-8') as f:
    auto = [line.strip() for line in f if line.strip()]
all_groups = sorted(list(set(scraped + auto)))
print(f'  scraped_groups.txt: {len(scraped)} grup')
print(f'  auto_groups.txt: {len(auto)} grup')
print(f'  Benzersiz Toplam: {len(all_groups)} grup')

# 6. Hardcoded gruplar (otomatik_katil.py icerisindeki)
print('\n=== HARDCODED GRUPLAR (otomatik_katil.py) ===')
with open('otomatik_katil.py', 'r', encoding='utf-8') as f:
    code = f.read()
import re
matches = re.findall(r'"([a-zA-Z0-9_\-]+)"', code[code.find('gruplar = ['):code.find('gruplar = [')+2000])
print(f'  Hardcoded hedef grup sayisi: {len(matches)}')

# 7. Banner dosyalari
print('\n=== BANNER DOSYALARI ===')
for banner in ['keyvadi_banner.png', 'lisansarena_banner.jpeg', 'froxy_banner.png']:
    if os.path.exists(banner):
        size_kb = os.path.getsize(banner) / 1024
        print(f'  OK {banner} ({size_kb:.1f} KB)')
    else:
        print(f'  EKSIK {banner}')

# 8. Gunun Firsatlari LisansArena fiyat kontrolu
print('\n=== GUNUN FIRSATLARI FIYAT KONTROLU ===')
# LisansArena icin Gemini Pro fiyati 99.99 TL olmali ama deals'de 69.99 yaziyorsa sorun var
# Kontrol edelim
idx = code.find('elif is_lisansarena:')
if idx > 0:
    deals_section = code[idx:idx+500]
    if '69.99' in deals_section:
        print('  UYARI: LisansArena deals bolumunde KeyVadi fiyati (69.99) kullaniliyor!')
    else:
        print('  OK: LisansArena deals bolumu kendi fiyatlarini kullaniyor.')

print('\n=== CHECK-UP TAMAMLANDI ===')
