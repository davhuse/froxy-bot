import asyncio, json, sys, os
sys.stdout.reconfigure(encoding='utf-8')
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest

api_id = int(os.environ.get('TELEGRAM_API_ID', '0') or 0)
api_hash = os.environ.get('TELEGRAM_API_HASH', '').strip()

KEYWORDS = [
    # Kupon & İndirim
    'kupon satış', 'kupon kod', 'indirim kod', 'indirim kupon',
    'hediye çeki', 'gift card', 'çek satış', 'promosyon kod',
    # Hesap & Dijital
    'hesap satış', 'dijital satış', 'dijital ürün', 'sanal ürün',
    'premium hesap', 'lisans satış', 'lisans kod',
    # Streaming & Entertainment
    'netflix hesap', 'spotify hesap', 'youtube premium',
    'disney plus', 'amazon prime', 'hbo max',
    'crunchyroll hesap', 'iptv satış', 'iptv grup',
    # AI & Yazılım
    'chatgpt hesap', 'chatgpt plus', 'yapay zeka hesap',
    'gemini pro', 'canva pro', 'adobe hesap',
    'grammarly hesap', 'office 365', 'windows lisans',
    # Gaming
    'oyun hesap satış', 'steam hesap', 'steam key',
    'discord nitro', 'game pass', 'ea play',
    'pubg hesap', 'valorant hesap', 'roblox hesap',
    'playstation hesap', 'xbox hesap', 'epic games',
    # Ticaret & Alım Satım
    'alım satım ticaret', 'sanal ticaret', 'shopier satış',
    'sanal alım satım', 'ticaret grup', 'freelance satış',
    # Sosyal Medya
    'telegram hesap', 'instagram hesap', 'tiktok hesap',
    'sosyal medya satış', 'takipçi satış',
    # VPN & Güvenlik
    'vpn hesap', 'vpn premium', 'kaspersky hesap', 'nordvpn',
    # Eğitim
    'udemy hesap', 'coursera hesap', 'eğitim hesap',
    # Kripto & Finans
    'kripto ticaret', 'binance hesap',
    # Genel
    'kod satış grubu', 'hesap pazarı', 'dijital pazar',
]

async def search_groups():
    with open('bot_config.json', 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    # Mevcut hedef listesini topla
    existing = set()
    try:
        with open('otomatik_katil.py', 'r', encoding='utf-8') as f:
            content = f.read()
        import re
        matches = re.findall(r'"([^"]+)"', content[:3000])
        for m in matches:
            existing.add(m.lower().lstrip('@').strip())
    except:
        pass
    if os.path.exists('gruplar.txt'):
        with open('gruplar.txt', 'r', encoding='utf-8') as f:
            for line in f:
                g = line.strip().lstrip('@')
                if g:
                    existing.add(g.lower())

    print(f'Mevcut hedef/korumali grup sayisi: {len(existing)}')
    print(f'Toplam anahtar kelime: {len(KEYWORDS)}')

    session_key = cfg.get('string_session_key_3')
    client = TelegramClient(StringSession(session_key), api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        print('HATA: Hesap yetkisiz!')
        return

    me = await client.get_me()
    print(f'Arama hesabi: {me.first_name} (ID: {me.id})')

    joined = set()
    async for dialog in client.iter_dialogs():
        if dialog.is_group or dialog.is_channel:
            if hasattr(dialog.entity, 'username') and dialog.entity.username:
                joined.add(dialog.entity.username.lower())
            joined.add(str(dialog.id).lower())
    print(f'Uye olunan grup sayisi: {len(joined)}\n')

    all_found = {}

    for keyword in KEYWORDS:
        try:
            result = await client(SearchRequest(q=keyword, limit=20))
            count = 0
            for chat in result.chats:
                username = getattr(chat, 'username', None)
                if not username:
                    continue
                title = getattr(chat, 'title', '') or ''
                members = getattr(chat, 'participants_count', None)
                is_broadcast = getattr(chat, 'broadcast', False)
                if is_broadcast:
                    continue
                if members and members < 50:
                    continue
                u_lower = username.lower()
                if u_lower in existing or u_lower in joined:
                    continue
                if u_lower not in all_found:
                    all_found[u_lower] = {
                        'username': username,
                        'title': title,
                        'members': members,
                        'keyword': keyword
                    }
                    count += 1
            status = f'  +{count} yeni' if count > 0 else '  -'
            print(f'{keyword:30s} {status}')
            await asyncio.sleep(1.5)
        except Exception as e:
            print(f'{keyword:30s}  HATA: {e}')
            await asyncio.sleep(5)

    print(f'\n{"="*70}')
    print(f'TOPLAM YENI GRUP: {len(all_found)}')
    print(f'{"="*70}\n')

    sorted_groups = sorted(all_found.values(), key=lambda x: x.get('members') or 0, reverse=True)

    for g in sorted_groups:
        members_str = str(g['members']) if g['members'] else '?'
        print(f'@{g["username"]:30s} | {members_str:>6s} uye | {g["title"][:40]}')

    with open('yeni_grup_sonuclari.json', 'w', encoding='utf-8') as f:
        json.dump(sorted_groups, f, ensure_ascii=False, indent=2)
    print(f'\nSonuclar yeni_grup_sonuclari.json dosyasina kaydedildi.')
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(search_groups())
