import asyncio
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest

sys.stdout.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
session1 = "1BJWap1sBu5KV1uEObjEZe-rlVuuHYuo-O2bLBaFvRYV4spqDLhyEURnGdwerOqZxDOVAeU9RhC0fYp9CfA5VSeZj4gEBaeQPUFcSZ9FAuekK1BuiV-dw0j3Ip88GM88f5LJiEV92z3uYKx6KbevaJhb_tWgLscE71fH1yFnKiCczMd1qNpeznDoan-L2eR9PISWMYjbiPgUDurr5mNChB0CTwzhdzx3DiSqzdNlJAwK8ciB0cfNOOc0cncb2r-pBjSpu4PK42Rczv5M6kuAUjQV6orOs8GSuctQ3yOF4vqTGeT9XXB7yQfFetro0sQjRghitSg6ZY5qOQ2IzSMffZWMjAuuYflg="

async def main():
    client = TelegramClient(StringSession(session1), api_id, api_hash)
    try:
        await client.connect()
        if await client.is_user_authorized():
            res = await client(SearchRequest(q="kuponceking", limit=5))
            for chat in res.chats:
                if chat.username and chat.username.lower() == "kuponceking":
                    print(f"Found via SearchRequest: @{chat.username}")
                    print(f"  join_request: {getattr(chat, 'join_request', 'NOT_FOUND')}")
                    print(f"  min: {getattr(chat, 'min', 'NOT_FOUND')}")
        else:
            print("Not authorized.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
