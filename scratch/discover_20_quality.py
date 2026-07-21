import asyncio
import json
import os
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel, Chat

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'
KEYWORDS = ['adobe lisans', 'netflix premium', 'youtube premium', 'smm hizmet', 'e ticaret', 'oyun hesap satış', 'trendyol satış', 'webmaster satış', 'freelance iş', 'dijital ürün']
NEGATIVE = ['sigara', 'vozol', 'vape', 'tekstil', 'casino', 'bahis', 'kumar', 'adult', 'porno', 'warez', 'illegal']

def load_set(*files):
    values = set()
    for path in files:
        if os.path.exists(path):
            with open(path, encoding='utf-8', errors='ignore') as f:
                values.update(line.strip().lower().lstrip('@') for line in f if line.strip())
    return values

async def main():
    with open('bot_config.json', encoding='utf-8') as f:
        cfg = json.load(f)
    sessions = [cfg.get('ad_string_session2'), cfg.get('ad_string_session3')]
    existing = load_set('gruplar.txt', 'scraped_groups.txt', 'auto_groups.txt', 'blacklist.txt')
    found = {}
    for index, session in enumerate(sessions, 2):
        if not session:
            continue
        client = TelegramClient(StringSession(session), API_ID, API_HASH)
        await client.connect()
        try:
            if not await client.is_user_authorized():
                print(f'account-{index}: unauthorized')
                continue
            me = await client.get_me()
            print(f'account-{index}: @{getattr(me, "username", None) or me.id}')
            for keyword in KEYWORDS:
                if len(found) >= 20:
                    break
                try:
                    result = await client(SearchRequest(q=keyword, limit=100))
                except Exception as exc:
                    print(f'  search {keyword!r} failed: {type(exc).__name__}')
                    continue
                for chat in result.chats:
                    if len(found) >= 20:
                        break
                    username = getattr(chat, 'username', None)
                    is_group = isinstance(chat, Chat) or (isinstance(chat, Channel) and not getattr(chat, 'broadcast', False))
                    title = (getattr(chat, 'title', '') or '').strip()
                    haystack = f'{username or ""} {title}'.lower()
                    members = getattr(chat, 'participants_count', 0) or 0
                    if not username or not is_group or members < 100 or any(word in haystack for word in NEGATIVE):
                        continue
                    key = username.lower()
                    if key in existing or key in found:
                        continue
                    found[key] = {'username': username, 'title': title, 'members': members, 'keyword': keyword}
                    print(f'  NEW {len(found):02d}: @{username} | {title} | {members} members')
                await asyncio.sleep(1)
        finally:
            await client.disconnect()
    with open('scraped_groups.txt', 'a', encoding='utf-8') as f:
        for key in found:
            f.write(key + '\n')
    print(f'FOUND_NEW={len(found)}')

if __name__ == '__main__':
    asyncio.run(main())
