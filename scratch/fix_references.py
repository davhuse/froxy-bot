import asyncio
import sys
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, EditAdminRequest
from telethon.tl.types import ChatAdminRights

sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'
c4hex_session_path = r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\c4hex_session.session"

reference_usernames = ["@FroxyReferans", "@KeyVadiReferans", "@LisansArenaReferans"]

async def fix_chat(client, username):
    print(f"\n--- Processing {username} ---")
    try:
        entity = await client.get_entity(username)
        print(f"   Successfully fetched entity for {username}. Type: {type(entity).__name__}")
        
        # 1. Delete advertising messages
        print("   Scanning recent messages to delete ads...")
        deleted_count = 0
        async for msg in client.iter_messages(entity, limit=50):
            # Check if sent by us
            if msg.out or msg.sender_id == (await client.get_me()).id:
                # Check if it looks like an ad message
                text_lower = (msg.text or "").lower()
                is_ad = any(kw in text_lower for kw in ["shopier", "canva", "netflix", "gemini", "grok", "fırsat", "premium", "lisans"])
                if is_ad:
                    await client.delete_messages(entity, msg.id)
                    deleted_count += 1
                    
        print(f"   Deleted {deleted_count} advertising messages.")
        
        # 2. Add Rose Bot (@MissRose_bot)
        print("   Adding Rose Bot (@MissRose_bot)...")
        try:
            rose_bot = await client.get_input_entity("@MissRose_bot")
            await client(InviteToChannelRequest(
                channel=entity,
                users=[rose_bot]
            ))
            print("   ✅ Rose Bot successfully added to the chat.")
            
            # Make Rose Bot admin if we have rights
            try:
                rights = ChatAdminRights(
                    post_messages=True,
                    delete_messages=True,
                    ban_users=True,
                    invite_users=True,
                    pin_messages=True,
                    add_admins=False,
                    anonymous=False,
                    manage_call=True,
                    other=True
                )
                await client(EditAdminRequest(
                    channel=entity,
                    user_id=rose_bot,
                    admin_rights=rights,
                    rank='Moderator'
                ))
                print("   ✅ Rose Bot promoted to Admin.")
            except Exception as admin_err:
                print(f"   ⚠️ Could not promote Rose Bot to Admin (maybe insufficient rights): {admin_err}")
                
        except Exception as add_err:
            print(f"   ⚠️ Could not add Rose Bot: {add_err}")
            
    except Exception as e:
        print(f"   ❌ Error processing {username}: {e}")

async def main():
    client = TelegramClient(c4hex_session_path, API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ Client unauthorized.")
            return
            
        for username in reference_usernames:
            await fix_chat(client, username)
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
