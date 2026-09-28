import asyncio
import sys
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8')

with open('test_account_session_string.txt', 'r', encoding='utf-8') as f:
    s = f.read().strip()

async def check():
    c = TelegramClient(StringSession(s), 20857997, 'ca29bc78298c92a2a09c25bb34586f1e')
    await c.connect()
    
    test_list = [
        'yazilimtoplulugu',
        'linux_tr',
        'bitgetturkiye',
        'KriptoSozlukTVPiyasaMuhabbeti',
        'yazilim0'
    ]
    
    for g in test_list:
        try:
            e = await c.get_entity(g)
            is_left = getattr(e, 'left', None)
            print(f"@{g}: title='{e.title}', left={is_left}")
            if is_left is not False:
                print(f"Joining @{g}...")
                await c(functions.channels.JoinChannelRequest(channel=e))
                await asyncio.sleep(2)
            m = await c.send_message(e, 'Selamlar herkese, iyi çalışmalar')
            print(f"SUCCESS: sent to @{g}, msg id {m.id}")
            await asyncio.sleep(1)
            await c.delete_messages(e, [m.id])
        except errors.FloodWaitError as fwe:
            print(f"FAIL on @{g}: FloodWait {fwe.seconds}s")
        except Exception as ex:
            print(f"FAIL on @{g}: {type(ex).__name__}: {ex}")
        await asyncio.sleep(2)

    await c.disconnect()

if __name__ == '__main__':
    asyncio.run(check())
