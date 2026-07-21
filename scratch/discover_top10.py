import asyncio
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel, Chat

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open('bot_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

s2 = cfg.get('ad_string_session2')

sales_keywords = [
    'satış', 'ticaret', 'hesap alım', 'yazılım', 'shopier', 
    'sosyal medya', 'dijital lisans', 'reklam', 'epin', 'premium',
    'trendyol kupon', 'canva pro', 'brawl stars', 'uygun lisans'
]

async def discover_top_10():
    c = TelegramClient(StringSession(s2), api_id, api_hash)
    await c.connect()
    if not await c.is_user_authorized():
        print('❌ Auth error for Account 2')
        return

    print('🔍 Telegram Global Arama Başlatılıyor (Kaliteli Grup Taraması)...')

    # Load existing blacklist
    blacklist = set()
    if os.path.exists('blacklist.txt'):
        with open('blacklist.txt', 'r', encoding='utf-8', errors='ignore') as f:
            for l in f:
                if l.strip():
                    blacklist.add(l.strip().lower().replace('@', ''))

    found_groups = []
    seen_usernames = set()

    for kw in sales_keywords:
        if len(found_groups) >= 10:
            break
        print(f'🔎 Anahtar Kelime Aranıyor: "{kw}"...')
        try:
            res = await c(SearchRequest(q=kw, limit=50))
            for chat in res.chats:
                if len(found_groups) >= 10:
                    break
                    
                is_group = False
                if isinstance(chat, Channel) and not getattr(chat, 'broadcast', False):
                    is_group = True
                elif isinstance(chat, Chat):
                    is_group = True

                username = getattr(chat, 'username', None)
                if not is_group or not username:
                    continue

                u_lower = username.lower()
                if u_lower in seen_usernames or u_lower in blacklist:
                    continue

                members = getattr(chat, 'participants_count', 0) or 0
                title = chat.title or ''

                # Quality filter: Member count >= 200
                if members < 200:
                    continue

                seen_usernames.add(u_lower)
                found_groups.append({
                    'username': f'@{username}',
                    'title': title,
                    'members': members,
                    'keyword': kw
                })
                print(f'  ✨ BULUNDU ({len(found_groups)}/10): @{username} | {title} | 👥 {members} üye')
        except Exception as e:
            print(f'  ⚠️ Hata ({kw}): {e}')

        await asyncio.sleep(1.5)

    await c.disconnect()

    print('\n====================================================')
    print('          KEŞFEDİLEN İLK 10 KALİTELİ GRUP RAPORU    ')
    print('====================================================')
    for idx, g in enumerate(found_groups, 1):
        print(f'{idx}. {g["username"]} — {g["title"]} (👥 {g["members"]} Üye) [Kategori: {g["keyword"]}]')

    # Save to files
    if found_groups:
        added_count = 0
        with open('gruplar.txt', 'a', encoding='utf-8') as f:
            for g in found_groups:
                clean_u = g['username'].replace('@', '')
                f.write(f'{clean_u}\n')
                added_count += 1
        with open('scraped_groups.txt', 'a', encoding='utf-8') as f:
            for g in found_groups:
                clean_u = g['username'].replace('@', '')
                f.write(f'{clean_u}\n')

        print(f'\n✅ Bulunan {added_count} grup gruplar.txt ve scraped_groups.txt dosyalarına kaydedildi.')

if __name__ == '__main__':
    asyncio.run(discover_top_10())
