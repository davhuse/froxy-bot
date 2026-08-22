import asyncio
import sys
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

TARGETS = [
    "KodDeposuCom", "KodDeposu", "KodVadisi", "koddiyari", "Kodmerkezichat",
    "indirimmerkezininyeri", "indirimmerkezim", "firsatmerkezigrup"
]

async def check():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    for u in TARGETS:
        try:
            ent = await client.get_entity(u)
            full = await client(GetFullChannelRequest(ent))
            m_cnt = getattr(full.full_chat, 'participants_count', 0)
            banned = getattr(full.full_chat, 'default_banned_rights', None)
            send_banned = getattr(banned, 'send_messages', False) if banned else False
            msgs = await client.get_messages(ent, limit=5)
            print(f"@{u:22s} | Üye: {m_cnt:5d} | Yazma Banlı: {send_banned} | Mesaj sayısı: {len(msgs)}")
            if msgs:
                print(f"   Son mesaj: {msgs[0].date} -> {msgs[0].text[:60] if msgs[0].text else '[Medya]'}")
        except Exception as e:
            print(f"@{u:22s} | HATA: {e}")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(check())
