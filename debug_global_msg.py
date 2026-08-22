import asyncio
import sys
from telethon import TelegramClient
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import InputPeerEmpty, InputMessagesFilterEmpty
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

async def test_global():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    try:
        res = await client(SearchGlobalRequest(
            q="yemeksepeti kupon",
            filter=InputMessagesFilterEmpty(),
            min_date=None,
            max_date=None,
            offset_rate=0,
            offset_peer=InputPeerEmpty(),
            offset_id=0,
            limit=20
        ))
        print("Messages:", len(res.messages))
        print("Chats:", len(res.chats))
        for c in res.chats:
            u = getattr(c, 'username', '')
            t = getattr(c, 'title', '')
            is_mega = getattr(c, 'megagroup', False)
            print(f"Chat: @{u:24s} | Title: {t[:25]} | Megagroup: {is_mega}")
    except Exception as e:
        print("Error:", type(e), e)
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(test_global())
