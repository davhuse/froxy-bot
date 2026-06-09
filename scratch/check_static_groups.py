import asyncio
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import InviteRequestSentError

sys.stdout.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
session1 = "1BJWap1sBu5KV1uEObjEZe-rlVuuHYuo-O2bLBaFvRYV4spqDLhyEURnGdwerOqZxDOVAeU9RhC0fYp9CfA5VSeZj4gEBaeQPUFcSZ9FAuekK1BuiV-dw0j3Ip88GM88f5LJiEV92z3uYKx6KbevaJhb_tWgLscE71fH1yFnKiCczMd1qNpeznDoan-L2eR9PISWMYjbiPgUDurr5mNChB0CTwzhdzx3DiSqzdNlJAwK8ciB0cfNOOc0cncb2r-pBjSpu4PK42Rczv5M6kuAUjQV6orOs8GSuctQ3yOF4vqTGeT9XXB7yQfFetro0sQjRghitSg6ZY5qOQ2IzSMffZWMjAuuYflg="

gruplar = [
    "ilanticaret", "Nightsatis", "alimsatimmerkezii", "kuponceking",
    "-1001572316417", "kuponsatimalim", "indirimkodusatis", "ticaretsaha",
    "ticaretforumofficial", "ticaretguvenilir", "kuponsatisgrup",
    "kuponhesapsatis", "kuponsatislari0", "TsmTicaret", "reklamreferans",
    "sosyalmedyaalimsatimticaret", "YuceKuponSatis"
]

async def main():
    client = TelegramClient(StringSession(session1), api_id, api_hash)
    try:
        await client.connect()
        if await client.is_user_authorized():
            for g in gruplar:
                # Skip numeric IDs for direct joining username checks
                if g.startswith("-") or g.isdigit():
                    print(f"Skipping numeric ID: {g}")
                    continue
                try:
                    chat = await client.get_entity(g)
                    join_request = getattr(chat, 'join_request', False)
                    print(f"Group: @{g} | Title: {chat.title} | Join Request Flag: {join_request}")
                except Exception as ex:
                    print(f"Error checking {g}: {ex}")
        else:
            print("Not authorized.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
