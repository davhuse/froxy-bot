import asyncio
import json
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, EditAdminRequest
from telethon.tl.types import ChatAdminRights

sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("bot_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

sessions = {
    "Hesap #1 (Froxy)": cfg.get("ad_string_session", ""),
    "Hesap #2 (KeyVadi)": cfg.get("ad_string_session2", "") or cfg.get("ad_string_session_2", ""),
    "Hesap #3 (LisansArena)": cfg.get("ad_string_session3", "") or cfg.get("ad_string_session_3", "")
}

async def try_add_rose(session_key, session_name, target_channel):
    if not session_key:
        print(f"Skipping {session_name} for {target_channel} (empty session).")
        return False
        
    client = TelegramClient(StringSession(session_key), API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"[{session_name}] Unauthorized.")
            return False
            
        me = await client.get_me()
        print(f"[{session_name}] Logged in as: {me.first_name} (@{me.username})")
        
        entity = await client.get_entity(target_channel)
        print(f"[{session_name}] Fetched entity for {target_channel}: Title='{entity.title}'")
        
        # Try inviting MissRose_bot
        print(f"[{session_name}] Inviting @MissRose_bot to {target_channel}...")
        rose = await client.get_input_entity("@MissRose_bot")
        await client(InviteToChannelRequest(channel=entity, users=[rose]))
        print(f"[{session_name}] ✅ Rose Bot invited to {target_channel}!")
        
        # Promote to admin
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
            await client(EditAdminRequest(channel=entity, user_id=rose, admin_rights=rights, rank='Moderator'))
            print(f"[{session_name}] ✅ Rose Bot promoted to Admin in {target_channel}!")
        except Exception as adm_err:
            print(f"[{session_name}] ⚠️ Could not promote Rose Bot: {adm_err}")
            
        return True
    except Exception as e:
        print(f"[{session_name}] ❌ Failed for {target_channel}: {e}")
        return False
    finally:
        await client.disconnect()

async def main():
    for ch in ["@KeyVadiReferans", "@LisansArenaReferans"]:
        print(f"\n========================================\nTarget: {ch}\n========================================")
        for s_name, s_key in sessions.items():
            success = await try_add_rose(s_key, s_name, ch)
            if success:
                break

if __name__ == "__main__":
    asyncio.run(main())
