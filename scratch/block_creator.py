import asyncio
import json
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import DeleteHistoryRequest
from telethon.tl.functions.contacts import BlockRequest

api_id = 26772719
api_hash = "f11aab22ed30e1dfd49ba8e5470d0da8"

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    with open("bot_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        
    s2 = config.get("ad_string_session2", "")
    if not s2:
        print("Session 2 (KeyVadi) not found.")
        return

    client = TelegramClient(StringSession(s2), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print("Account 2 is NOT authorized.")
        return

    print("Connected to Account 2 (KeyVadi). Searching for 'creator' in recent chats...")
    
    found = False
    async for dialog in client.iter_dialogs(limit=50):
        if dialog.is_user:
            user = dialog.entity
            fname = getattr(user, 'first_name', '') or ''
            uname = getattr(user, 'username', '') or ''
            
            if 'creator' in fname.lower() or 'creator' in uname.lower():
                print(f"Found target: {fname} (@{uname}) [ID: {user.id}]")
                found = True
                
                print("Deleting history for both sides...")
                try:
                    await client(DeleteHistoryRequest(
                        peer=user,
                        max_id=0,
                        just_clear=False,
                        revoke=True
                    ))
                    print("History deleted successfully.")
                except Exception as e:
                    print(f"Failed to delete history: {e}")
                    
                print("Blocking user...")
                try:
                    await client(BlockRequest(id=user.id))
                    print("User blocked successfully.")
                except Exception as e:
                    print(f"Failed to block user: {e}")
                
                break

    if not found:
        print("No user containing 'creator' was found in recent chats.")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
