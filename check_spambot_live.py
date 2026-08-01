import asyncio, json, sys
sys.stdout.reconfigure(encoding='utf-8')
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def check_spam():
    print('======================================================================')
    print('       LIVE TELEGRAM SPAMBOT AUDIT FOR ALL 3 ACCOUNTS                 ')
    print('======================================================================\n')
    
    with open('bot_config.json', 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    keys = [
        ('FroxyOnline (+905015291021)', cfg.get('string_session_key')),
        ('KeyVadiOnline (+905056798875)', cfg.get('string_session_key_2')),
        ('LisansArenaOnline (+14176608361)', cfg.get('string_session_key_3'))
    ]

    for label, s_str in keys:
        try:
            client = TelegramClient(StringSession(s_str), api_id, api_hash)
            await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                print(f'✅ {label}: Connected! ID: {me.id} | Name: {me.first_name}')
                
                try:
                    spambot = await client.get_entity('SpamBot')
                    await client.send_message(spambot, '/start')
                    await asyncio.sleep(2.5)
                    async for msg in client.iter_messages(spambot, limit=1):
                        txt = msg.text or ''
                        if 'Good news' in txt or 'no limits' in txt or 'free' in txt or 'kısıtlama yok' in txt or 'hiçbir kısıtlama' in txt:
                            print(f'   🎉 SpamBot Yanıtı: TERTEREMİZ (Hiçbir Kısıtlama Yok!) -> "{txt[:80]}..."')
                        else:
                            print(f'   ℹ️ SpamBot Yanıtı: "{txt[:100]}..."')
                except Exception as sb_err:
                    print(f'   SpamBot denetim notu: {sb_err}')
            else:
                print(f'❌ {label}: Oturum yetkisiz.')
            await client.disconnect()
        except Exception as e:
            print(f'❌ {label} Hata: {e}')

if __name__ == '__main__':
    asyncio.run(check_spam())
