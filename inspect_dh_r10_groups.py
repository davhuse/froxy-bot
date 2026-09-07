import asyncio
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

targets = [
    "kuponsat",
    "kuponkodalsat",
    "firsatdolu",
    "trendyolyemekindirim",
    "My_kod_all",
    "brandiumdh",
    "epinkod",
    "KuponFirsat",
    "yemeksepetiindirimlerii",
    "migros_indirim_kupon",
    "turnaindirim",
    "uber_indirim_turkiye",
    "yemeksepetikodlari",
    "yemeksepeti_kupon_al"
]

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for u in targets:
        try:
            ent = await client.get_entity(u)
            is_mega = isinstance(ent, Channel) and ent.megagroup
            banned = ent.default_banned_rights if isinstance(ent, Channel) else None
            can_send = not (banned and banned.send_messages) if is_mega else False
            
            members = 0
            if isinstance(ent, Channel):
                full = await client(GetFullChannelRequest(ent))
                members = getattr(full.full_chat, 'participants_count', 0)

            print(f"@{u:<24} | Mega: {is_mega} | Yazma: {can_send} | Üye: {members} | {ent.title}")
            if is_mega and can_send:
                msgs = await client.get_messages(ent, limit=3)
                for m in msgs:
                    if m.raw_text:
                        print(f"   - {m.raw_text.replace(chr(10), ' ')[:75]}")
        except Exception as e:
            print(f"@{u:<24} | Hata: {e}")
        await asyncio.sleep(0.5)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
