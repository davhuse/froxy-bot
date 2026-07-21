import asyncio
import time
import sys
import os
from telethon import TelegramClient

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import firestore_helper

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'


async def main():
    client = TelegramClient('c4hex_session', API_ID, API_HASH)
    await client.start()
    try:
        for username, text in [
            ('@KeyVadiSatisBot', f'Canva Pro test-count {time.time_ns()}'),
            ('@LisansArenaBot', f'Adobe test-count {time.time_ns()}'),
        ]:
            entity = await client.get_entity(username)
            before = (await client.get_messages(entity, limit=1))[0].id
            await client.send_message(entity, text)
            sent = await client.get_messages(entity, limit=1)
            sent_id = next((m.id for m in sent if m.out), None)
            await asyncio.sleep(10)
            replies = []
            async for message in client.iter_messages(entity, limit=20):
                if message.id > before and not message.out:
                    replies.append(message)
            scope = 'keyvadi_sales' if 'KeyVadi' in username else 'lisansarena_sales'
            claim_doc = f'dm_event_{scope}_{entity.id}_{sent_id}'
            print(username, 'sent_id=', sent_id, 'claim=', firestore_helper.get_document(claim_doc), 'reply_count=', len(replies), 'ids=', [m.id for m in replies], 'texts=', [(m.raw_text or '')[:100] for m in replies])
    finally:
        await client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
