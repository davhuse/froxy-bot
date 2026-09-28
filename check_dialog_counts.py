import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from check_sessions import vars

api_id = int(vars['TELEGRAM_API_ID'])
api_hash = vars['TELEGRAM_API_HASH']

async def check_dialogs(name, session_str):
    if not session_str:
        print(f"{name}: NO SESSION")
        return
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        dialogs = await client.get_dialogs(limit=100)
        groups = [d for d in dialogs if d.is_group or d.is_channel]
        print(f"{name} (@{me.username}, phone {me.phone}): Total dialogs={len(dialogs)}, Groups/Channels={len(groups)}")
    else:
        print(f"{name}: NOT AUTHORIZED")
    await client.disconnect()

async def main():
    await check_dialogs("LisansArena", vars.get('AD_STRING_SESSION_LISANSARENA'))
    await check_dialogs("Jarvis", vars.get('AD_STRING_SESSION_JARVIS'))
    await check_dialogs("KeyVadi", vars.get('AD_STRING_SESSION_KEYVADI'))
    await check_dialogs("Froxy", vars.get('AD_STRING_SESSION_FROXY'))

asyncio.run(main())
