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

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

candidates = [
    "kuponhesap",
    "xfnje",
    "kazandriiro",
    "hesapsatistrsohbet",
    "emirhesap",
    "HESAP_ALIM_SATIM",
    "kodbankasisohbet1",
    "indirimKulubu1",
    "kuponindirimsohbet",
    "ibrahimkoknar",
    "siyaketoneri",
    "indirimkaplani_sohbet"
]

verified = []

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for uname in candidates:
        try:
            entity = await client.get_entity(uname)
            if not isinstance(entity, Channel) or not entity.megagroup:
                continue

            banned = entity.default_banned_rights
            can_send = True
            if banned and banned.send_messages:
                can_send = False

            full = await client(GetFullChannelRequest(entity))
            members = getattr(full.full_chat, 'participants_count', 0)

            msgs = await client.get_messages(entity, limit=3)
            last_date = str(msgs[0].date)[:10] if msgs else "Bilinmiyor"

            sample_text = msgs[0].raw_text.replace('\n', ' ')[:70] if msgs and msgs[0].raw_text else ""

            verified.append({
                "username": uname,
                "title": entity.title,
                "members": members,
                "can_send": can_send,
                "last_active": last_date,
                "sample": sample_text
            })
            print(f"✅ @{uname:<23} | Üye: {members:<5} | Yazma: {can_send} | Son: {last_date} | {entity.title}")
        except Exception as e:
            print(f"❌ @{uname}: {e}")
        await asyncio.sleep(0.5)

    await client.disconnect()

    with open("strictly_verified_10_groups.json", "w", encoding="utf-8") as f:
        json.dump(verified, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())
