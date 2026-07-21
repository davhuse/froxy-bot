import asyncio
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

user_specified_groups = [
    'YuceKuponSatis',
    'kuponceking',
    'ticaretguvenilir',
    'TicaretGrubuuu',
    'kuponsatimalim',
    'KuponindirimPazari'
]

with open('bot_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

s2 = cfg.get('ad_string_session2')
s3 = cfg.get('ad_string_session3')

async def sync_new_joined_groups():
    print('====================================================')
    print('   YENİ KATILINAN GRUPLARI SENKRONİZE ETME        ')
    print('====================================================\n')

    # Load existing lists
    existing = set()
    for fname in ['gruplar.txt', 'scraped_groups.txt']:
        if os.path.exists(fname):
            with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    u = line.strip().lower().replace('@', '')
                    if u:
                        existing.add(u)

    # Remove from blacklist if present
    blacklist = set()
    if os.path.exists('blacklist.txt'):
        with open('blacklist.txt', 'r', encoding='utf-8', errors='ignore') as f:
            for l in f:
                u = l.strip().lower().replace('@', '')
                if u:
                    blacklist.add(u)

    new_discovered = set()

    # 1. Add user specified groups
    for g in user_specified_groups:
        g_clean = g.lower()
        new_discovered.add(g_clean)
        print(f'📌 Kullanıcının Eklenecek Dediği Grup: @{g}')

    # 2. Scan Account 2 joined dialogs
    if s2:
        try:
            c2 = TelegramClient(StringSession(s2), api_id, api_hash)
            await c2.connect()
            if await c2.is_user_authorized():
                async for dialog in c2.iter_dialogs():
                    if dialog.is_group or dialog.is_channel:
                        un = getattr(dialog.entity, 'username', None)
                        if un:
                            new_discovered.add(un.lower())
            await c2.disconnect()
        except Exception as e:
            print(f'⚠️ Account 2 scan error: {e}')

    # 3. Scan Account 3 joined dialogs
    if s3:
        try:
            c3 = TelegramClient(StringSession(s3), api_id, api_hash)
            await c3.connect()
            if await c3.is_user_authorized():
                async for dialog in c3.iter_dialogs():
                    if dialog.is_group or dialog.is_channel:
                        un = getattr(dialog.entity, 'username', None)
                        if un:
                            new_discovered.add(un.lower())
            await c3.disconnect()
        except Exception as e:
            print(f'⚠️ Account 3 scan error: {e}')

    # Filter out blacklisted
    final_added = []
    for g in new_discovered:
        if g in blacklist:
            # If user explicitly specified, unblacklist
            if g in [x.lower() for x in user_specified_groups]:
                blacklist.remove(g)
                print(f'🔓 Kullanıcının eklediği @{g} kara listeden çıkarıldı.')
        final_added.append(g)

    # Save updated blacklist
    with open('blacklist.txt', 'w', encoding='utf-8') as f:
        for b in sorted(list(blacklist)):
            f.write(f'{b}\n')

    # Append to gruplar.txt and scraped_groups.txt
    added_count = 0
    with open('gruplar.txt', 'a', encoding='utf-8') as f_g, open('scraped_groups.txt', 'a', encoding='utf-8') as f_s:
        for g in final_added:
            if g not in existing:
                f_g.write(f'{g}\n')
                f_s.write(f'{g}\n')
                existing.add(g)
                added_count += 1
                print(f'✨ YENİ GRUP EKLENDİ: @{g}')

    print(f'\n✅ Toplam {added_count} adet yeni grup gruplar.txt ve scraped_groups.txt dosyalarına kaydedildi.')
    print('🚀 Reklam botu sonraki blast turunda bu gruplara da doğrudan ilan gönderecektir.')

if __name__ == '__main__':
    asyncio.run(sync_new_joined_groups())
