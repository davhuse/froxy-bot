import asyncio
import sys
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import InviteRequestSentError, FloodWaitError

sys.stdout.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
session1 = "1BJWap1sBu5KV1uEObjEZe-rlVuuHYuo-O2bLBaFvRYV4spqDLhyEURnGdwerOqZxDOVAeU9RhC0fYp9CfA5VSeZj4gEBaeQPUFcSZ9FAuekK1BuiV-dw0j3Ip88GM88f5LJiEV92z3uYKx6KbevaJhb_tWgLscE71fH1yFnKiCczMd1qNpeznDoan-L2eR9PISWMYjbiPgUDurr5mNChB0CTwzhdzx3DiSqzdNlJAwK8ciB0cfNOOc0cncb2r-pBjSpu4PK42Rczv5M6kuAUjQV6orOs8GSuctQ3yOF4vqTGeT9XXB7yQfFetro0sQjRghitSg6ZY5qOQ2IzSMffZWMjAuuYflg="

# User requested static groups
specified_groups = ["ReklamOnliene", "letgoilanlari", "alcaponesat"]

# Auto discovered groups to choose from (max 10 to join)
auto_groups = [
    "sanalalimsatimticaret",
    "ticar4t",
    "buy_Panel_Premium_Members_Adder",
    "bayanaktuel",
    "indirimfirsatburada",
    "yapay_zekatahminleri",
    "indirimdeal",
    "indirimciyizbiz",
    "indirimcin",
    "indirimlergrubu",
    "indirimlisi",
    "indirimhep"
]

async def join_group(client, username):
    try:
        print(f"Attempting to join @{username}...")
        chat = await client.get_entity(username)
        
        # Check if requires request
        if getattr(chat, 'join_request', False):
            print(f"  ❌ Skip @{username}: Requires admin approval (join_request is True)")
            return False, "requires_approval"
            
        await client(JoinChannelRequest(chat))
        print(f"  ✅ Successfully joined @{username}!")
        return True, "joined"
    except InviteRequestSentError:
        print(f"  ❌ Skip @{username}: Sent invite request (requires approval)")
        return False, "requires_approval"
    except FloodWaitError as fwe:
        print(f"  ⏳ Flood wait of {fwe.seconds} seconds required.")
        return False, f"flood_{fwe.seconds}"
    except Exception as e:
        print(f"  ❌ Error joining @{username}: {type(e).__name__} - {e}")
        return False, str(e)

async def main():
    client = TelegramClient(StringSession(session1), api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("Not authorized")
            return
            
        # Get currently joined group usernames to avoid joining again
        joined_usernames = set()
        print("Fetching currently joined groups...")
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                username = getattr(dialog.entity, 'username', None)
                if username:
                    joined_usernames.add(username.lower())
        print(f"Already joined in {len(joined_usernames)} groups.")
        
        # 1. Join specified groups
        print("\n--- Joining Specified Groups ---")
        for g in specified_groups:
            if g.lower() in joined_usernames:
                print(f"  ℹ️ Already member of @{g}")
            else:
                success, reason = await join_group(client, g)
                if success:
                    joined_usernames.add(g.lower())
                await asyncio.sleep(3)
                
        # 2. Join up to 10 auto groups
        print("\n--- Joining Up to 10 Auto-Scraped Groups ---")
        joined_count = 0
        for g in auto_groups:
            if joined_count >= 10:
                print("🎯 Reached maximum join limit of 10 auto groups.")
                break
                
            if g.lower() in joined_usernames:
                print(f"  ℹ️ Already member of @{g}")
                # We count this as joined towards targeting, but let's see if we should join new ones
                continue
                
            success, reason = await join_group(client, g)
            if success:
                joined_usernames.add(g.lower())
                joined_count += 1
            await asyncio.sleep(5)
            
        print(f"\nExecution finished! Successfully joined {joined_count} auto groups.")
        
    except Exception as e:
        print(f"Error in main: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
