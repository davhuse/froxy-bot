import asyncio, sys
sys.stdout.reconfigure(encoding='utf-8')
from telethon import TelegramClient

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def check_live_telegram():
    print('======================================================================')
    print('       DIRECT TELEGRAM API AUDIT (LIVE FROM TELEGRAM SERVERS)         ')
    print('======================================================================\n')
    
    client = TelegramClient('login_keyvadi_0505', api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print('❌ KeyVadi session not authorized!')
        await client.disconnect()
        return

    me = await client.get_me()
    print(f'✅ Connected Account: {me.first_name} {me.last_name or ""} (@{me.username or "yok"}) | ID: {me.id}')
    print(f'   Phone: +{me.phone}\n')

    dialogs = await client.get_dialogs(limit=50)
    print('=== RECENT MESSAGED GROUPS & CHATS STRAIGHT FROM TELEGRAM ===')
    
    count = 0
    for d in dialogs:
        if d.is_group or d.is_channel:
            uname = getattr(d.entity, 'username', '') or ''
            uname_str = f'@{uname}' if uname else 'Özel/Gizli Grup'
            
            async for msg in client.iter_messages(d.entity, limit=5, from_user='me'):
                count += 1
                date_str = msg.date.strftime('%Y-%m-%d %H:%M:%S UTC')
                text_snippet = (msg.text or '')[:80].replace('\n', ' ')
                print(f'{count}. Group: {d.title} ({uname_str})')
                print(f'   • Sent Date (UTC): {date_str}')
                print(f'   • Message Text: "{text_snippet}..."\n')
                break
                
        if count >= 10:
            break
            
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(check_live_telegram())
