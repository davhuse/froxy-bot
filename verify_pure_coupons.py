import asyncio
import json
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Channel

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open("session_key_output.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

pure_candidates = [
    "kuponindirimsohbet",
    "indirimkaplani_sohbet",
    "indirimzkanal",
    "indirimce",
    "UCUZSEPET",
    "ibrahimkoknar",
    "migros_indirim",
    "xfnje",
    "indirimkodbul",
    "indirimKulubu1"
]

results = []

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for uname in pure_candidates:
        try:
            entity = await client.get_entity(uname)
            if not isinstance(entity, Channel) or not entity.megagroup:
                print(f"❌ @{uname}: Not a supergroup")
                continue

            full = await client(GetFullChannelRequest(entity))
            banned = entity.default_banned_rights
            can_send = True
            if banned and banned.send_messages:
                can_send = False

            members = getattr(full.full_chat, 'participants_count', 0)
            slowmode = getattr(full.full_chat, 'slowmode_seconds', 0) or 0

            # Get last message to check recent activity
            msgs = await client.get_messages(entity, limit=1)
            last_date = str(msgs[0].date) if msgs else "Yok"

            results.append({
                "username": uname,
                "title": entity.title,
                "members": members,
                "can_send": can_send,
                "slowmode": slowmode,
                "last_active": last_date
            })
            print(f"✅ @{uname:<23} | Üye: {members:<5} | Yazma: {can_send} | Son Mesaj: {last_date[:10]} | Başlık: {entity.title}")
        except Exception as e:
            print(f"❌ @{uname}: {e}")
        await asyncio.sleep(1)

    await client.disconnect()

    with open("verified_pure_coupon_groups.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())
