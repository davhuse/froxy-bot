import asyncio
import json
import sys
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, EditAdminRequest
from telethon.tl.types import ChatAdminRights

sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("bot_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

bot_tokens = {
    "KeyVadi Bot": (cfg.get("bot_token"), "@KeyVadiReferans"),
    "LisansArena Bot": (cfg.get("lisansarena_bot_token"), "@LisansArenaReferans"),
    "Froxy Bot": (cfg.get("froxy_bot_token"), "@FroxyReferans")
}

async def try_bot_add_rose(bot_name, bot_token, target_channel):
    if not bot_token:
        print(f"Skipping {bot_name} (no token).")
        return
        
    client = TelegramClient(f'scratch/{bot_name.replace(" ", "_")}_session', API_ID, API_HASH)
    try:
        await client.start(bot_token=bot_token)
        me = await client.get_me()
        print(f"[{bot_name}] Logged in as bot @{me.username}")
        
        entity = await client.get_entity(target_channel)
        print(f"[{bot_name}] Fetched {target_channel}: Title='{entity.title}'")
        
        rose = await client.get_input_entity("@MissRose_bot")
        await client(InviteToChannelRequest(channel=entity, users=[rose]))
        print(f"[{bot_name}] ✅ Rose bot added to {target_channel}!")
        
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
        print(f"[{bot_name}] ✅ Rose bot promoted to admin in {target_channel}!")
    except Exception as e:
        print(f"[{bot_name}] ❌ Failed for {target_channel}: {e}")
    finally:
        await client.disconnect()

async def main():
    for name, (token, ch) in bot_tokens.items():
        await try_bot_add_rose(name, token, ch)

if __name__ == "__main__":
    asyncio.run(main())
