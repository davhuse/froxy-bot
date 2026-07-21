import asyncio
import sys
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest, InviteToChannelRequest, EditAdminRequest
from telethon.tl.types import ChatAdminRights

sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'
c4hex_session_path = r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\c4hex_session.session"

channels = ["@FroxyReferans", "@KeyVadiReferans", "@LisansArenaReferans"]

async def inspect_and_clean():
    client = TelegramClient(c4hex_session_path, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Client unauthorized.")
        return
        
    me = await client.get_me()
    print(f"Logged in as: {me.first_name} (ID: {me.id}, Username: @{me.username})")
    
    for ch_name in channels:
        print(f"\n========================================\nINSPECTING {ch_name}\n========================================")
        try:
            entity = await client.get_entity(ch_name)
            print(f"Entity: ID={entity.id}, Title='{entity.title}', Type={type(entity).__name__}")
            
            # Check permissions / participant info
            try:
                full_ch = await client(GetFullChannelRequest(channel=entity))
                print(f"Can set username: {getattr(full_ch.full_chat, 'can_set_username', 'N/A')}")
            except Exception as e:
                print(f"GetFullChannel error: {e}")
                
            # Scan last 100 messages for ads
            print("Scanning last 100 messages for ads...")
            ads_to_delete = []
            async for msg in client.iter_messages(entity, limit=100):
                text = msg.text or ""
                # Check for typical ad text patterns
                is_ad = any(kw in text.lower() for kw in ["shopier.com", "satın alabilir", "fiyatı:", "keyvadisatisbot", "lisansarenabot", "otomatik teslimat"])
                if is_ad:
                    ads_to_delete.append(msg)
                    print(f"  Found Ad (ID {msg.id}, Date {msg.date}): {text[:60].replace(chr(10), ' ')}...")
                    
            if ads_to_delete:
                print(f"Deleting {len(ads_to_delete)} ad messages...")
                for m in ads_to_delete:
                    try:
                        await client.delete_messages(entity, m.id)
                        print(f"  Deleted msg ID {m.id}")
                    except Exception as del_err:
                        print(f"  Failed to delete msg ID {m.id}: {del_err}")
            else:
                print("No ad messages found in recent history.")

            # Try to add MissRose_bot
            print("Attempting to invite @MissRose_bot...")
            try:
                rose = await client.get_input_entity("@MissRose_bot")
                await client(InviteToChannelRequest(channel=entity, users=[rose]))
                print("  ✅ MissRose_bot invited successfully!")
                
                # Promote to admin
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
                print("  ✅ MissRose_bot promoted to Admin!")
            except Exception as invite_err:
                print(f"  ⚠️ Invite/Promote MissRose_bot failed: {invite_err}")

        except Exception as e:
            print(f"❌ Error inspecting {ch_name}: {e}")
            
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(inspect_and_clean())
