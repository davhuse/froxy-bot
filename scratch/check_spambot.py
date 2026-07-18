import urllib.request
import json
import ssl
import sys
import asyncio
from telethon import TelegramClient, events

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def check_spambot(session_str, account_name):
    print(f"\n--- Checking SpamBot status for {account_name} ---")
    from telethon.sessions import StringSession
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"❌ {account_name} is not authorized!")
            return
            
        me = await client.get_me()
        print(f"✅ Connected as: {me.first_name} (@{me.username or 'NoUsername'}) | ID: {me.id}")
        
        # Send message to SpamBot
        spambot = 'SpamBot'
        await client.send_message(spambot, '/start')
        print("Sent /start to @SpamBot, waiting for reply...")
        
        # Wait for reply
        reply_received = False
        for _ in range(10):
            await asyncio.sleep(1)
            async for msg in client.iter_messages(spambot, limit=1):
                if msg.sender_id != me.id and not msg.out:
                    print(f"\nSpamBot Response:\n{msg.text}\n")
                    reply_received = True
                    break
            if reply_received:
                break
        if not reply_received:
            print("❌ No response received from SpamBot within 10 seconds.")
            
        await client.disconnect()
    except Exception as e:
        print(f"❌ Error for {account_name}: {e}")

async def main():
    # Fetch configs from Render
    req = urllib.request.Request('https://veridia-bot.onrender.com/api/config')
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            cfg = json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print("Failed to fetch Render config:", e)
        return
        
    session2 = cfg.get("ad_string_session2")
    session3 = cfg.get("ad_string_session3")
    
    if session2:
        await check_spambot(session2, "Hesap #2 (KeyVadi)")
    else:
        print("No session string found for Hesap #2")
        
    if session3:
        await check_spambot(session3, "Hesap #3 (LisansArena)")
    else:
        print("No session string found for Hesap #3")

if __name__ == "__main__":
    asyncio.run(main())
