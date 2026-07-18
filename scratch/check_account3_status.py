import asyncio
import json
import os
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError, UserBannedInChannelError, ChannelPrivateError

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def main():
    if not os.path.exists("bot_config.json"):
        print("bot_config.json not found!")
        return
        
    with open("bot_config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
        
    session3 = cfg.get("ad_string_session3", cfg.get("ad_string_session_3", ""))
    if not session3:
        print("ad_string_session3 not found in config!")
        return
        
    client = TelegramClient(StringSession(session3), api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("Account #3 is NOT authorized!")
        return
        
    me = await client.get_me()
    print(f"Logged in as: {me.first_name} (@{me.username}) | ID: {me.id}")
    
    print("\nListing all current dialogs:")
    dialogs = await client.get_dialogs()
    groups_joined = []
    for d in dialogs:
        if d.is_group or d.is_channel:
            username = getattr(d.entity, 'username', '') or ''
            try:
                name_str = d.name.encode('utf-8', errors='replace').decode('utf-8')
            except:
                name_str = "???"
            print(f"  - [{d.id}] {name_str} (@{username})")
            if username:
                groups_joined.append(username.lower())
                
    print(f"\nTotal joined groups/channels: {len(groups_joined)}")
    
    # Try joining one of the target groups to test restriction status
    test_group = "ticaretforumofficial"
    print(f"\nTesting join to @{test_group}...")
    try:
        entity = await client.get_entity(test_group)
        await client(JoinChannelRequest(entity))
        print("  Join SUCCESSFUL!")
    except FloodWaitError as e:
        print(f"  FAILED: FloodWait for {e.seconds} seconds")
    except UserBannedInChannelError:
        print("  FAILED: User Banned In Channel")
    except ChannelPrivateError:
        print("  FAILED: Channel is private/restricted")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__} - {e}")
        
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
