import asyncio
import re
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsAdmins, Channel

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    target = "kuponsat"
    ent = await client.get_entity(target)
    full = await client(GetFullChannelRequest(ent))
    
    print("=== @kuponsat BİLGİLERİ ===")
    print(f"Başlık: {ent.title}")
    print(f"Hakkında: {full.full_chat.about}")
    print(f"Sabitlenen Mesaj ID: {full.full_chat.pinned_msg_id}")
    print(f"Linked Chat (Kanal/Grup): {full.full_chat.linked_chat_id}")

    if full.full_chat.pinned_msg_id:
        try:
            pinned = await client.get_messages(ent, ids=full.full_chat.pinned_msg_id)
            print(f"\n📌 SABİTLENMİŞ MESAJ:\n{pinned.raw_text}\n")
        except Exception as e:
            pass

    print("\n=== YÖNETİCİLER ===")
    try:
        admins = await client(GetParticipantsRequest(
            channel=ent,
            filter=ChannelParticipantsAdmins(),
            offset=0,
            limit=20,
            hash=0
        ))
        for p in admins.users:
            print(f"Admin: {p.first_name} (@{p.username}) - ID: {p.id}")
    except Exception as e:
        pass

    # Extract all @ links from recent 40 messages
    print("\n=== RECENT MESSAGES LINKS ===")
    msgs = await client.get_messages(ent, limit=40)
    links = set()
    for m in msgs:
        txt = m.raw_text or ""
        for u in re.findall(r'@([a-zA-Z0-9_]{5,32})', txt):
            links.add(u.lower())
        for l in re.findall(r't\.me/([a-zA-Z0-9_]{5,32})', txt):
            links.add(l.lower())
    print("Extracted links:", links)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
