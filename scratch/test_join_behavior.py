import asyncio
import sys
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Channel, Chat
from telethon.errors import InviteRequestSentError, FloodWaitError

sys.stdout.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
session1 = "1BJWap1sBu5KV1uEObjEZe-rlVuuHYuo-O2bLBaFvRYV4spqDLhyEURnGdwerOqZxDOVAeU9RhC0fYp9CfA5VSeZj4gEBaeQPUFcSZ9FAuekK1BuiV-dw0j3Ip88GM88f5LJiEV92z3uYKx6KbevaJhb_tWgLscE71fH1yFnKiCczMd1qNpeznDoan-L2eR9PISWMYjbiPgUDurr5mNChB0CTwzhdzx3DiSqzdNlJAwK8ciB0cfNOOc0cncb2r-pBjSpu4PK42Rczv5M6kuAUjQV6orOs8GSuctQ3yOF4vqTGeT9XXB7yQfFetro0sQjRghitSg6ZY5qOQ2IzSMffZWMjAuuYflg="

async def main():
    client = TelegramClient(StringSession(session1), api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("Not authorized")
            return
            
        keywords = ["kupon", "ticaret", "yazılım"]
        checked = set()
        
        for kw in keywords:
            print(f"\nSearching for '{kw}'...")
            res = await client(SearchRequest(q=kw, limit=10))
            for chat in res.chats:
                if not chat.username or chat.username.lower() in checked:
                    continue
                checked.add(chat.username.lower())
                
                is_group = False
                if isinstance(chat, Channel):
                    if not getattr(chat, 'broadcast', False):
                        is_group = True
                elif isinstance(chat, Chat):
                    is_group = True
                    
                if not is_group:
                    continue
                    
                join_request = getattr(chat, 'join_request', False)
                print(f"Checking @{chat.username} (Join Request attribute: {join_request})...")
                
                # If join_request is False, let's see what happens when we try to join
                if not join_request:
                    try:
                        # Attempt to join (dry run sort of, we'll leave immediately if joined successfully)
                        # We use JoinChannelRequest
                        print(f"  Attempting to join @{chat.username}...")
                        result = await client(JoinChannelRequest(chat))
                        print(f"  ✅ Joined instantly! Result: {type(result).__name__}")
                        
                        # Leave group so we don't pollute the account
                        from telethon.tl.functions.channels import LeaveChannelRequest
                        await client(LeaveChannelRequest(chat))
                        print(f"  Left @{chat.username}")
                    except InviteRequestSentError as e:
                        print(f"  ⚠️ InviteRequestSentError raised! Group requires approval even though join_request is False: {e}")
                    except FloodWaitError as fwe:
                        print(f"  ⏳ FloodWaitError: {fwe.seconds}s. Skipping...")
                        await asyncio.sleep(5)
                    except Exception as e:
                        print(f"  Failed to join: {type(e).__name__} - {e}")
                else:
                    print("  Skipped: join_request is True")
                
                await asyncio.sleep(2)
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
