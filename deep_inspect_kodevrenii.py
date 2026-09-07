import asyncio
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

    target = "kodevrenii"
    ent = await client.get_entity(target)
    full = await client(GetFullChannelRequest(ent))
    
    print("=== KOD EVRENİ BİLGİLERİ ===")
    print(f"Başlık: {ent.title}")
    print(f"Hakkında: {full.full_chat.about}")
    print(f"Sabitlenen Mesaj ID: {full.full_chat.pinned_msg_id}")
    print(f"Linked Chat (Kanal/Grup): {full.full_chat.linked_chat_id}")

    if full.full_chat.pinned_msg_id:
        try:
            pinned = await client.get_messages(ent, ids=full.full_chat.pinned_msg_id)
            print(f"\n📌 SABİTLENMİŞ MESAJ:\n{pinned.raw_text}\n")
        except Exception as e:
            print(f"Pinned message error: {e}")

    print("\n=== YÖNETİCİLER (ADMİNLER) ===")
    try:
        admins = await client(GetParticipantsRequest(
            channel=ent,
            filter=ChannelParticipantsAdmins(),
            offset=0,
            limit=50,
            hash=0
        ))
        for p in admins.users:
            print(f"Admin: {p.first_name} (@{p.username}) - ID: {p.id}")
    except Exception as e:
        print(f"Admin fetch error: {e}")

    print("\n=== SON 25 MESAJDAKİ TÜM KULLANICILAR VE LİNKLER ===")
    msgs = await client.get_messages(ent, limit=25)
    for m in msgs:
        sender_name = getattr(m.sender, 'first_name', '')
        sender_user = getattr(m.sender, 'username', '')
        text = (m.raw_text or '').replace('\n', ' ')
        print(f"[{sender_name} @{sender_user}]: {text[:100]}")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
