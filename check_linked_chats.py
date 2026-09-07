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

with open("session_key_output.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

channels_to_check = [
    "indirimdeal", "indirimkurt3144", "indirimkaplani", "onual_firsat",
    "onemlifirsatlar", "indirimg", "indirimz", "amazonozel", "firsatbudur",
    "sicakfirsatlar", "donanimhaber", "trendyolindirimleri", "hepsiburadaindirim"
]

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for ch_name in channels_to_check:
        try:
            entity = await client.get_entity(ch_name)
            full = await client(GetFullChannelRequest(entity))
            linked_chat_id = full.full_chat.linked_chat_id
            if linked_chat_id:
                linked_entity = await client.get_entity(linked_chat_id)
                can_send = True
                banned = getattr(linked_entity, 'default_banned_rights', None)
                if banned and banned.send_messages:
                    can_send = False
                members = getattr(linked_entity, 'participants_count', 0)
                print(f"✅ {ch_name} -> Linked Chat: @{linked_entity.username} ({linked_entity.title}) | Members: {members} | CanSend: {can_send}")
            else:
                print(f"ℹ️ {ch_name} -> No linked chat")
        except Exception as e:
            print(f"❌ {ch_name} -> {e}")
        await asyncio.sleep(1)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
