import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("froxy_session_output.txt", "r", encoding="utf-8") as f:
    SESSION_STRING = f.read().strip()

async def test_fast():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    me = await client.get_me()
    print(f"Connected as {me.first_name} ({me.id})")
    
    test_candidates = ["me7alimsatim", "kuponsat", "alimsatimmerkezii", "letgoilanlari", "ticaretyapn"]
    for u in test_candidates:
        try:
            entity = await client.get_entity(u)
            is_mega = getattr(entity, 'megagroup', False) or getattr(entity, 'gigagroup', False)
            is_broad = getattr(entity, 'broadcast', False)
            print(f"Candidate: @{u} | Title: {entity.title} | Mega: {is_mega} | Broad: {is_broad}")
            
            msgs = await client.get_messages(entity, limit=15)
            senders = set(m.sender_id for m in msgs if m and m.sender_id)
            print(f"  -> Fetched {len(msgs)} msgs | Unique senders: {len(senders)} | Latest date: {msgs[0].date if msgs else 'N/A'}")
            if msgs and msgs[0].text:
                print(f"  -> Latest msg: {msgs[0].text[:60]}")
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Error @{u}: {e}")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_fast())
