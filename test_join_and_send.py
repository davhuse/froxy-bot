import asyncio
import os
import sys
from telethon import TelegramClient, functions, types, errors
from telethon.sessions import StringSession

API_ID = 20857997
API_HASH = "ca29bc78298c92a2a09c25bb34586f1e"

SESSION = ""
with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
    SESSION = f.read().strip()

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Test account is NOT authorized!")
        return

    me = await client.get_me()
    print(f"Logged in as: {me.first_name} (@{me.username}) ID: {me.id} Phone: +{me.phone}")

    # Check dialogs to see what groups the test account is currently in
    dialogs = await client.get_dialogs(limit=50)
    joined_usernames = set()
    for d in dialogs:
        if d.is_channel or d.is_group:
            entity = d.entity
            username = getattr(entity, 'username', None)
            if username:
                joined_usernames.add(username.lower())
    print(f"Current joined groups count: {len(joined_usernames)}")
    print(f"Joined usernames: {list(joined_usernames)[:10]}")

    # Test group from 'sohbet':
    # 'TurkceSohbetler' was sent to earlier.
    # What about 'Kocaeli_sohbet_muhabbet' or 'sohbetimi' or 'dostlarkahvesitr'?
    candidates = ["Kocaeli_sohbet_muhabbet", "sohbetimi", "dostlarkahvesitr", "turkiyediyalogu", "turkcesohbetgrubuu"]
    
    for cand in candidates:
        is_already_in = cand.lower() in joined_usernames
        print(f"\nTesting candidate: @{cand} (Already in dialogs: {is_already_in})")
        
        try:
            entity = await client.get_entity(cand)
            print(f"Entity fetched: ID={entity.id}, Title={getattr(entity, 'title', None)}, Broadcast={getattr(entity, 'broadcast', False)}")
            
            if getattr(entity, 'broadcast', False):
                print(f"SKIPPING: @{cand} is a broadcast channel, cannot post!")
                continue

            # Check if participant or join
            joined = False
            try:
                # Try getting permissions
                perms = await client.get_permissions(entity, me)
                print(f"Current permissions in @{cand}: is_participant={perms.is_participant}, send_messages={perms.send_messages}")
                if not perms.is_participant:
                    print(f"Joining @{cand} via JoinChannelRequest...")
                    res = await client(functions.channels.JoinChannelRequest(channel=entity))
                    print(f"Join result: {type(res).__name__}")
                    joined = True
                    await asyncio.sleep(2)
            except errors.UserNotParticipantError:
                print(f"UserNotParticipantError -> Joining @{cand}...")
                res = await client(functions.channels.JoinChannelRequest(channel=entity))
                print(f"Join result: {type(res).__name__}")
                joined = True
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Permission check / join info: {type(e).__name__}: {e}")
                # Try direct join
                try:
                    res = await client(functions.channels.JoinChannelRequest(channel=entity))
                    print(f"JoinChannelRequest: {type(res).__name__}")
                    joined = True
                    await asyncio.sleep(2)
                except errors.UserAlreadyParticipantError:
                    print("Already participant.")
                except Exception as je:
                    print(f"Direct join failed: {type(je).__name__}: {je}")

            # Re-check permissions
            try:
                perms_after = await client.get_permissions(entity, me)
                print(f"Permissions after join: is_participant={perms_after.is_participant}, send_messages={perms_after.send_messages}")
            except Exception as pe:
                print(f"Permissions check failed: {pe}")

            # Send test message
            print(f"Attempting to send message to @{cand}...")
            sent_msg = await client.send_message(entity, "Selamlar herkese, iyi günler")
            print(f"SUCCESS! Message sent to @{cand}, ID={sent_msg.id}")
            break # One successful test is enough to verify

        except errors.FloodWaitError as fwe:
            print(f"FLOOD WAIT on @{cand}: wait {fwe.seconds}s")
        except errors.ChatWriteForbiddenError as cwf:
            print(f"WRITE FORBIDDEN on @{cand}: {cwf}")
        except Exception as e:
            print(f"ERROR on @{cand}: {type(e).__name__}: {e}")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
