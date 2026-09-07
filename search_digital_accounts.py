import asyncio
import json
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

with open("blacklist.txt", "r", encoding="utf-8") as f:
    blacklist = {line.strip().lower() for line in f if line.strip()}

with open("gruplar.txt", "r", encoding="utf-8") as f:
    existing_groups = {line.strip().lower().replace("@", "") for line in f if line.strip()}

queries = [
    "hesap alım", "hesap satım", "lisans alım", "lisans satım",
    "chatgpt hesap", "canva pro", "netflix hesap", "dijital ürünler",
    "premium hesaplar", "uygun hesap", "ucuz hesap", "dijital pazar",
    "hesap pazarı", "lisans pazarı", "çek pazarı", "kupon pazarı",
    "kod pazarı", "dijital ticaret", "hesap ticaret"
]

FORBIDDEN = [
    "pubg", "brawl", "pes", "oyun", "etsy", "araba", "oto",
    "kripto", "forex", "escort", "kumar", "bahis", "gay", "nargile",
    "tiktok", "instagram", "takipçi", "takipci", "dizi", "film",
    "porn", "sex", "karı", "sahte", "para", "vape", "puff", "sigara"
]

results = {}

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for q in queries:
        try:
            res = await client(SearchRequest(q=q, limit=40))
            for chat in res.chats:
                if not (isinstance(chat, Channel) and chat.megagroup):
                    continue
                uname = chat.username
                if not uname:
                    continue
                u_low = uname.lower()
                t_low = (chat.title or "").lower()

                if u_low in blacklist or u_low in existing_groups or u_low in results:
                    continue

                if any(bad in u_low or bad in t_low for bad in FORBIDDEN):
                    continue

                banned = chat.default_banned_rights
                if banned and banned.send_messages:
                    continue

                members = getattr(chat, 'participants_count', 0) or 0
                if members < 50:
                    continue

                msgs = await client.get_messages(chat, limit=5)
                if not msgs:
                    continue

                last_date = str(msgs[0].date)[:10]
                sample = msgs[0].raw_text.replace('\n', ' ')[:90] if msgs[0].raw_text else ""

                results[u_low] = {
                    "username": uname,
                    "title": chat.title,
                    "members": members,
                    "last_active": last_date,
                    "sample": sample
                }
                print(f"  🛒 @{uname:<22} | {members:<5} üye | Son: {last_date} | {chat.title}")
            await asyncio.sleep(1)
        except Exception:
            pass

    await client.disconnect()
    print(f"\nToplam: {len(results)}")
    with open("digital_account_groups.json", "w", encoding="utf-8") as f:
        json.dump(list(results.values()), f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())
