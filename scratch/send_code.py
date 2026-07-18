import asyncio
import sys
import json
import ssl
import urllib.request
from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
phone = sys.argv[1]

async def main():
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    print(f"Sending code request for {phone}...")
    hash_obj = await client.send_code_request(phone)
    
    session_string = client.session.save()
    
    data = {
        'phone': phone,
        'phone_code_hash': hash_obj.phone_code_hash,
        'session_string': session_string
    }
    
    with open('pending_login.json', 'w') as f:
        json.dump(data, f)
        
    print(f"Code requested. Hash saved to pending_login.json")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
