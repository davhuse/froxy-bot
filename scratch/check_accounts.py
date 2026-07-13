import asyncio
import json
import os
import urllib.request
import sys

# Windows terminal encoding fix
sys.stdout.reconfigure(encoding='utf-8')

from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def test_string_session(session_str, name):
    if not session_str:
        print(f"[FAIL] {name}: Session string is empty.")
        return False
    try:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)
        await client.connect()
        authorized = await client.is_user_authorized()
        if authorized:
            me = await client.get_me()
            print(f"[OK] {name}: Connected successfully! User: @{me.username or 'NoUsername'} (ID: {me.id}, Phone: +{me.phone})")
            await client.disconnect()
            return True
        else:
            print(f"[FAIL] {name}: Connection failed or session not authorized.")
            await client.disconnect()
            return False
    except Exception as e:
        print(f"[FAIL] {name}: Error connecting: {e}")
        return False

def test_bot_token(token, name):
    if not token:
        print(f"[FAIL] {name}: Bot token is empty.")
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode())
            if res_data.get("ok"):
                result = res_data["result"]
                print(f"[OK] {name}: Token is valid! Bot: @{result['username']} (ID: {result['id']})")
                return True
            else:
                print(f"[FAIL] {name}: API returned error: {res_data}")
                return False
    except Exception as e:
        print(f"[FAIL] {name}: Error testing token: {e}")
        return False

async def main():
    print("=== HABİL TELEGRAM BOT SYSTEM DETAILED CHECK-UP ===")
    print("---------------------------------------------------------")
    
    if not os.path.exists("bot_config.json"):
        print("Error: bot_config.json not found!")
        return

    try:
        with open("bot_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        print(f"Error: bot_config.json could not be read! {e}")
        return

    # Check Bot Tokens
    print("\n[1] Testing Telegram Bot Tokens...")
    print("-------------------------------------")
    test_bot_token(cfg.get("bot_token"), "KeyVadi Satis Bot (@KeyVadiSatisBot)")
    test_bot_token(cfg.get("froxy_bot_token"), "Froxy AI Destek Bot (@FroxyDestekBOT)")
    test_bot_token(cfg.get("lisansarena_bot_token"), "LisansArena Bot (@LisansArenaBot)")

    # Check String Sessions
    print("\n[2] Testing Ad Sender Accounts...")
    print("-------------------------------------------------")
    session1 = cfg.get("ad_string_session", "")
    session2 = cfg.get("ad_string_session2", cfg.get("ad_string_session_2", ""))
    session3 = cfg.get("ad_string_session3", cfg.get("ad_string_session_3", ""))
    
    await test_string_session(session1, "Account #1 (Main Ad Account)")
    await test_string_session(session2, "Account #2 (Second Ad Account)")
    await test_string_session(session3, "Account #3 (LisansArena Ad Account)")

    print("\n---------------------------------------------------------")
    print("=== CHECK-UP COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(main())
