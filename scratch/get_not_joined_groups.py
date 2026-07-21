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

with open('bot_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

s2 = cfg.get('ad_string_session2')
s3 = cfg.get('ad_string_session3')

async def list_not_joined():
    # 1. Load target groups from gruplar.txt & scraped_groups.txt
    target_groups = set()
    for fname in ['gruplar.txt', 'scraped_groups.txt']:
        if os.path.exists(fname):
            with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    u = line.strip().lower().replace('@', '').replace('https://t.me/', '')
                    if u:
                        target_groups.add(u)

    # 2. Load blacklist
    blacklist = set()
    if os.path.exists('blacklist.txt'):
        with open('blacklist.txt', 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                u = line.strip().lower().replace('@', '').replace('https://t.me/', '')
                if u:
                    blacklist.add(u)

    # Filter out blacklisted
    valid_targets = [g for g in target_groups if g not in blacklist]

    # 3. Connect Account 2 (@KeyVadiOnline) and get joined dialogs
    kv_joined = set()
    c2 = TelegramClient(StringSession(s2), api_id, api_hash)
    await c2.connect()
    if await c2.is_user_authorized():
        async for dialog in c2.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                un = getattr(dialog.entity, 'username', None)
                if un:
                    kv_joined.add(un.lower())
    await c2.disconnect()

    # 4. Connect Account 3 (@LisansArenaOnline) and get joined dialogs
    la_joined = set()
    c3 = TelegramClient(StringSession(s3), api_id, api_hash)
    await c3.connect()
    if await c3.is_user_authorized():
        async for dialog in c3.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                un = getattr(dialog.entity, 'username', None)
                if un:
                    la_joined.add(un.lower())
    await c3.disconnect()

    # Compute not joined for KeyVadi & LisansArena
    kv_not_joined = [g for g in valid_targets if g not in kv_joined]
    la_not_joined = [g for g in valid_targets if g not in la_joined]
    all_not_joined = sorted(list(set(kv_not_joined).union(set(la_not_joined))))

    print('====================================================')
    print('      HENÜZ ÜYE OLUNMAMIŞ / BEKLEYEN GRUPLAR RAPORU  ')
    print('====================================================')
    print(f'📊 Toplam Kaliteli Hedef Grup : {len(valid_targets)}')
    print(f'✅ KeyVadi Katıldığı Grup     : {len(kv_joined)}')
    print(f'✅ LisansArena Katıldığı Grup : {len(la_joined)}')
    print(f'⏳ Üye Olunmayı Bekleyen Grup : {len(all_not_joined)}\n')

    print('📌 HENÜZ ÜYE OLUNMAMIŞ GRUPLARIN LİSTESİ:')
    for idx, g in enumerate(all_not_joined, 1):
        kv_status = 'ÜYE' if g in kv_joined else 'ÜYE DEĞİL'
        la_status = 'ÜYE' if g in la_joined else 'ÜYE DEĞİL'
        print(f'{idx:>2}. @{g:<30} [KeyVadi: {kv_status} | LisansArena: {la_status}]')

if __name__ == '__main__':
    asyncio.run(list_not_joined())
