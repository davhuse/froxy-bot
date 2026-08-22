"""
DEBUG version: Show ALL groups found, why they were filtered, and sender details.
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import asyncio
import json
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import InputMessagesFilterEmpty, InputPeerEmpty

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open(r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\froxy_session_output.txt", "r") as f:
    SESSION_STRING = f.read().strip()

# Load exclusion lists
excluded = set()
with open(r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\gruplar.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip().lower()
        if line:
            excluded.add(line)

with open(r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\blacklist.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip().lower()
        if line and not line.startswith("-"):
            excluded.add(line)

print(f"Excluded groups: {len(excluded)}")

QUERIES = [
    "@AuraDijital",
    "@Cano31m", 
    "@Ventaru1234567890",
    "@Ferhatbey47",
    "Ventaru",
    "AuraDijital",
]

async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()
    print("Connected!\n")

    # Collect ALL chats with reason for filtering
    all_chats_seen = {}  # chat_id -> info
    all_senders = {}  # Track all unique senders across all results
    
    for query in QUERIES:
        print(f"=== Query: '{query}' ===")
        try:
            result = await client(SearchGlobalRequest(
                q=query,
                filter=InputMessagesFilterEmpty(),
                min_date=None, max_date=None,
                offset_rate=0, offset_peer=InputPeerEmpty(),
                offset_id=0, limit=100
            ))

            chats = {c.id: c for c in result.chats}
            users = {u.id: u for u in result.users}

            print(f"  Messages: {len(result.messages)}, Chats: {len(result.chats)}, Users: {len(result.users)}")

            # Show all chats from this query
            for c in result.chats:
                cid = c.id
                uname = getattr(c, 'username', None)
                title = getattr(c, 'title', '???')
                mega = getattr(c, 'megagroup', False)
                bcast = getattr(c, 'broadcast', False)
                members = getattr(c, 'participants_count', None)
                
                status = "OK"
                if not mega:
                    status = "SKIP:not_megagroup"
                elif bcast:
                    status = "SKIP:broadcast"
                elif not uname:
                    status = "SKIP:no_username"
                elif uname.lower() in excluded:
                    status = f"SKIP:excluded"
                
                if cid not in all_chats_seen:
                    all_chats_seen[cid] = {
                        'username': uname, 'title': title,
                        'megagroup': mega, 'broadcast': bcast,
                        'members': members, 'status': status,
                        'queries': [], 'trader_messages': []
                    }
                all_chats_seen[cid]['queries'].append(query)

            # Check each message's sender
            for msg in result.messages:
                if hasattr(msg.peer_id, 'channel_id'):
                    chat_id = msg.peer_id.channel_id
                elif hasattr(msg.peer_id, 'chat_id'):
                    chat_id = msg.peer_id.chat_id
                else:
                    continue

                # Get sender info
                sender_uid = None
                if hasattr(msg, 'from_id') and msg.from_id:
                    if hasattr(msg.from_id, 'user_id'):
                        sender_uid = msg.from_id.user_id
                    elif hasattr(msg.from_id, 'channel_id'):
                        sender_uid = msg.from_id.channel_id

                sender_uname = None
                sender_name = None
                if sender_uid and sender_uid in users:
                    u = users[sender_uid]
                    sender_uname = getattr(u, 'username', None)
                    first = getattr(u, 'first_name', '') or ''
                    last = getattr(u, 'last_name', '') or ''
                    sender_name = f"{first} {last}".strip()
                    all_senders[sender_uid] = {
                        'username': sender_uname, 'name': sender_name, 'id': sender_uid
                    }

                # Track if this is from a target trader
                target_unames = {'auradijital', 'cano31m', 'ventaru1234567890', 'ferhatbey47', 'craigkks'}
                target_ids = {1553279766}
                
                is_trader = False
                if sender_uname and sender_uname.lower() in target_unames:
                    is_trader = True
                elif sender_uid in target_ids:
                    is_trader = True

                if chat_id in all_chats_seen and is_trader:
                    all_chats_seen[chat_id]['trader_messages'].append({
                        'sender': sender_uname or sender_name or str(sender_uid),
                        'text': (msg.message or '')[:150],
                        'date': str(msg.date)
                    })

        except Exception as e:
            print(f"  ERROR: {e}")
        
        await asyncio.sleep(2)

    # Print summary
    print("\n" + "="*80)
    print("ALL CHATS FOUND ACROSS ALL QUERIES:")
    print("="*80)
    
    new_groups = []
    excluded_groups = []
    skipped_groups = []
    
    for cid, info in sorted(all_chats_seen.items(), key=lambda x: x[1]['status']):
        uname = info['username'] or 'NO_USERNAME'
        print(f"\n  [{info['status']}] @{uname} - {info['title']}")
        print(f"    Members: {info['members']}, Megagroup: {info['megagroup']}, Broadcast: {info['broadcast']}")
        print(f"    Queries: {info['queries']}")
        if info['trader_messages']:
            print(f"    TRADER MESSAGES ({len(info['trader_messages'])}):")
            for tm in info['trader_messages'][:3]:
                print(f"      [{tm['sender']}] {tm['text'][:100]}")
        
        if info['status'] == 'OK':
            new_groups.append(info)
        elif info['status'] == 'SKIP:excluded':
            excluded_groups.append(info)
        else:
            skipped_groups.append(info)

    print(f"\n\nSUMMARY:")
    print(f"  NEW (not excluded, valid megagroup): {len(new_groups)}")
    print(f"  EXCLUDED (in gruplar/blacklist): {len(excluded_groups)}")
    print(f"  SKIPPED (not megagroup/broadcast/no username): {len(skipped_groups)}")

    # Show all unique senders that matched trader criteria
    print(f"\n  UNIQUE SENDERS SEEN: {len(all_senders)}")
    target_unames = {'auradijital', 'cano31m', 'ventaru1234567890', 'ferhatbey47', 'craigkks'}
    for sid, sinfo in all_senders.items():
        if sinfo['username'] and sinfo['username'].lower() in target_unames:
            print(f"    ** TRADER: @{sinfo['username']} ({sinfo['name']}) ID:{sinfo['id']}")

    # Save detailed results
    output = {
        'new_groups': new_groups,
        'excluded_groups': [{'username': g['username'], 'title': g['title']} for g in excluded_groups],
        'skipped_groups': [{'username': g['username'], 'title': g['title'], 'reason': g['status']} for g in skipped_groups]
    }
    with open(r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\trader_debug_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    await client.disconnect()

asyncio.run(main())
