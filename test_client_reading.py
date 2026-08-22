import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def test_session(s_file):
    with open(s_file) as f:
        s = f.read().strip()
    cl = TelegramClient(StringSession(s), api_id, api_hash)
    await cl.connect()
    me = await cl.get_me()
    print(f"{s_file} user: {me.first_name} ID: {me.id}")
    for target in ['me7alimsatim', 'kuponsat', 'ticaretZ']:
        try:
            e = await cl.get_entity(target)
            is_mega = getattr(e, 'megagroup', False) or getattr(e, 'gigagroup', False)
            is_broad = getattr(e, 'broadcast', False)
            msgs = await cl.get_messages(e, limit=5)
            print(f"Target: @{target} | Title: {e.title} | Mega: {is_mega} | Broad: {is_broad} | Msgs: {len(msgs)}")
            if msgs:
                print(f"  Latest msg: {msgs[0].date} | Sender: {msgs[0].sender_id} | Text: {msgs[0].text[:60] if msgs[0].text else 'no text'}")
        except Exception as ex:
            print(f"Target @{target} Error: {ex}")
    await cl.disconnect()

if __name__ == '__main__':
    print("Testing session_7384.txt:")
    asyncio.run(test_session('session_7384.txt'))
