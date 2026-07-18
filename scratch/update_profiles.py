import asyncio
import urllib.request
import json
import ssl
import sys
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get_render_config():
    req = urllib.request.Request('https://veridia-bot.onrender.com/api/config')
    with urllib.request.urlopen(req, context=ctx) as r:
        return json.loads(r.read().decode('utf-8'))

async def process_account(session_str, name, username, bot_username, bio):
    print(f"\nProcessing {name}...")
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print(f"  ❌ Not authorized for {name}")
        await client.disconnect()
        return

    # Update Name and Bio
    try:
        await client(UpdateProfileRequest(first_name=name, last_name='', about=bio))
        print(f"  ✅ Name and bio updated to {name}")
    except Exception as e:
        print(f"  ⚠️ Error updating name/bio: {e}")

    # Update Username
    try:
        await client(UpdateUsernameRequest(username=username))
        print(f"  ✅ Username updated to @{username}")
    except Exception as e:
        print(f"  ⚠️ Error updating username: {e}")

    # Download profile photo from Bot
    try:
        print(f"  Fetching photo from @{bot_username}...")
        bot_entity = await client.get_entity(bot_username)
        photo_path = f"{username}_photo.jpg"
        
        # Download the photo
        await client.download_profile_photo(bot_entity, file=photo_path)
        print(f"  Downloaded photo to {photo_path}")
        
        # Upload it
        uploaded_file = await client.upload_file(photo_path)
        await client(UploadProfilePhotoRequest(file=uploaded_file))
        print(f"  ✅ Profile photo updated successfully!")
        
        # Clean up
        if os.path.exists(photo_path):
            os.remove(photo_path)
            
    except Exception as e:
        print(f"  ⚠️ Error handling profile photo: {e}")
        
    await client.disconnect()

async def main():
    cfg = get_render_config()
    session2 = cfg.get("ad_string_session2", "")
    session3 = cfg.get("ad_string_session3", "")
    
    if session2:
        await process_account(session2, "KeyVadi Destek", "KeyVadiSatis", "KeyVadiSatisBot", "KeyVadi - Dijital Lisans ve Abonelik Merkezi")
    if session3:
        await process_account(session3, "LisansArena Destek", "LisansArenaSatis", "LisansArenaBot", "LisansArena - Premium Hesap ve Yazılım Çözümleri")

        
if __name__ == '__main__':
    asyncio.run(main())
