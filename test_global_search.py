import asyncio
from telethon import TelegramClient
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import InputPeerEmpty, InputMessagesFilterEmpty
from telethon.sessions import StringSession

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("froxy_session_output.txt", "r", encoding="utf-8") as f:
    s_froxy = f.read().strip()

async def test_search_global():
    client = TelegramClient(StringSession(s_froxy), API_ID, API_HASH)
    await client.connect()
    me = await client.get_me()
    print(f"Connected as {me.first_name}")
    
    queries = ["yemeksepeti kupon satılık", "chatgpt plus satılık", "lisans key satılık", "kupon alım satım dm"]
    for q in queries:
        try:
            res = await client(SearchGlobalRequest(
                q=q,
                filter=InputMessagesFilterEmpty(),
                min_date=None,
                max_date=None,
                offset_rate=0,
                offset_peer=InputPeerEmpty(),
                offset_id=0,
                limit=15
            ))
            print(f"\nQuery: '{q}' -> Msgs: {len(res.messages)}, Chats: {len(res.chats)}")
            chat_map = {c.id: c for c in res.chats}
            for m in res.messages[:3]:
                peer = m.peer_id
                cid = getattr(peer, 'channel_id', None) or getattr(peer, 'chat_id', None)
                chat = chat_map.get(cid)
                if chat:
                    u = getattr(chat, 'username', 'no_username')
                    title = getattr(chat, 'title', 'no_title')
                    is_mega = getattr(chat, 'megagroup', False)
                    print(f"  Chat: @{u} | Title: {title} | Mega: {is_mega} | Date: {m.date}")
                    print(f"  Msg: {m.message[:70] if m.message else ''}")
        except Exception as e:
            print(f"Query '{q}' Error: {e}")
        await asyncio.sleep(1.0)
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_search_global())
