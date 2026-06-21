import asyncio
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import DeletePhotosRequest

sys.stdout.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
session_str = "1AZWarzgBu1IAur9L2pribQqBOpT09D4jZzfROzj7hZWpWFoPa1NdaedUpIztycyCt02VrxkndRr3bfnaFaKaQ4OGr-o-_2xY8ZEsGDRhY6TlTp2gCh2PpWHgW8OvhOCgvxGb8EeXJE450oqpba9SCLCQblQTNPzNNH4w5GoTtRf3khANW-vRKmx4ggkCeDo11yBTtXQQTWMen2xHpymfa9Yf8GaijkhxGRjIEKlBxWcs_t7lEmWs9EOz1LiIglQeJIz2KnVUt_2RGoJ7g7veXsq8-jsvlN6ndnMZd7WAv0GMjSD_Q86Vzw2DQ0Uh2qHiNcss2p4b_HZzPkZKZPgk1zROg4LQTJs="

async def main():
    print("Connecting to Account #2 (@KeyVadi) to reset profile...")
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ Client is not authorized!")
            return
            
        me = await client.get_me()
        print(f"Logged in as: @{me.username} ({me.first_name} {me.last_name or ''}) ID: {me.id}")
        
        # 1. Update Profile (Name & Bio)
        print("Resetting name to 'Habil' and clearing bio...")
        await client(UpdateProfileRequest(
            first_name="Habil",
            last_name="",
            about=""
        ))
        print("✅ Profile name and bio updated.")
        
        # 2. Update Username (Clear it)
        if me.username:
            print(f"Removing username @{me.username}...")
            try:
                await client(UpdateUsernameRequest(username=""))
                print("✅ Username removed.")
            except Exception as ue:
                print(f"⚠️ Could not remove username: {ue}")
                
        # 3. Delete Profile Pictures
        print("Fetching and deleting profile pictures...")
        photos = []
        async for photo in client.iter_profile_photos('me'):
            photos.append(photo)
        if photos:
            try:
                await client(DeletePhotosRequest(photos))
                print(f"✅ Deleted {len(photos)} profile pictures.")
            except Exception as pe:
                print(f"⚠️ Could not delete profile pictures: {pe}")
        else:
            print("No profile pictures found.")
            
        print("🎉 Profile reset complete!")
    except Exception as e:
        print(f"❌ Error resetting profile: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
