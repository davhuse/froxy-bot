import asyncio
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import CheckChatInviteRequest
from telethon.tl.types import ChatInvite, ChatInviteAlready

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    try:
        res = await client(CheckChatInviteRequest(hash="1ikzfQnOiEQ3ZDI0"))
        if isinstance(res, ChatInvite):
            print(f"Title: {res.title} | Members: {res.participants_count} | Is Megagroup: {res.megagroup}")
        elif isinstance(res, ChatInviteAlready):
            print(f"Already in: {res.chat.title}")
    except Exception as e:
        print(f"Error: {e}")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
