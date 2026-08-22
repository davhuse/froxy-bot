"""
Search for groups where specific traders have posted messages.
Uses SearchGlobalRequest with EXACT usernames.
Filters against gruplar.txt and blacklist.txt.
"""

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

# Load exclusion lists (only gruplar.txt and blacklist.txt as TRUE exclusion)
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

print(f"Loaded {len(excluded)} excluded groups")

# Exact trader usernames to search for
TRADER_QUERIES = [
    # Primary: exact usernames
    "AuraDijital",
    "Cano31m",
    "Ventaru1234567890",
    "Ferhatbey47",
    # Also try with @ prefix variations and display names
    "@AuraDijital",
    "@Cano31m",
    "@Ventaru1234567890",
    "@Ferhatbey47",
    # Display name variations
    "Aura Dijital",
    "Ferhat B47",
    "John Snow",
    "craigkks",
    # Ventaru's known ad phrases (distinctive)
    "Ventaru",
]

async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()
    print("Client connected!")

    # Track all discovered groups: {username_lower: {info}}
    all_groups = {}
    # Track which traders posted in which groups
    group_traders = {}  # username_lower -> set of trader usernames found

    for query in TRADER_QUERIES:
        print(f"\n--- Searching: '{query}' ---")
        try:
            result = await client(SearchGlobalRequest(
                q=query,
                filter=InputMessagesFilterEmpty(),
                min_date=None,
                max_date=None,
                offset_rate=0,
                offset_peer=InputPeerEmpty(),
                offset_id=0,
                limit=100
            ))

            # Build chat lookup
            chats = {}
            for c in result.chats:
                chats[c.id] = c

            # Build user lookup
            users = {}
            for u in result.users:
                users[u.id] = u

            print(f"  Found {len(result.messages)} messages, {len(result.chats)} chats")

            for msg in result.messages:
                # Get the chat this message belongs to
                if hasattr(msg.peer_id, 'channel_id'):
                    chat_id = msg.peer_id.channel_id
                elif hasattr(msg.peer_id, 'chat_id'):
                    chat_id = msg.peer_id.chat_id
                else:
                    continue

                chat = chats.get(chat_id)
                if not chat:
                    continue

                # Only megagroups (not channels/broadcasts)
                is_megagroup = getattr(chat, 'megagroup', False)
                is_broadcast = getattr(chat, 'broadcast', False)
                if not is_megagroup or is_broadcast:
                    continue

                username = getattr(chat, 'username', None)
                if not username:
                    continue

                username_lower = username.lower()

                # Skip excluded groups
                if username_lower in excluded:
                    continue

                # Get sender info
                sender_id = getattr(msg, 'from_id', None)
                if sender_id and hasattr(sender_id, 'user_id'):
                    sender_uid = sender_id.user_id
                else:
                    sender_uid = getattr(msg, 'sender_id', None)

                sender_username = None
                sender_name = None
                if sender_uid and sender_uid in users:
                    u = users[sender_uid]
                    sender_username = getattr(u, 'username', None)
                    first = getattr(u, 'first_name', '') or ''
                    last = getattr(u, 'last_name', '') or ''
                    sender_name = f"{first} {last}".strip()

                # Check if sender is one of our target traders
                target_usernames = {
                    'auradijital', 'cano31m', 'ventaru1234567890', 'ferhatbey47', 'craigkks'
                }
                target_ids = {1553279766}  # Ventaru's known ID

                is_target_trader = False
                matched_trader = None
                if sender_username and sender_username.lower() in target_usernames:
                    is_target_trader = True
                    matched_trader = sender_username
                elif sender_uid in target_ids:
                    is_target_trader = True
                    matched_trader = f"ID:{sender_uid}"

                # Store group info
                if username_lower not in all_groups:
                    all_groups[username_lower] = {
                        'username': username,
                        'title': getattr(chat, 'title', ''),
                        'participants_count': getattr(chat, 'participants_count', None),
                        'messages_found': [],
                        'has_target_trader': False,
                        'matched_traders': set(),
                        'query_hits': set()
                    }

                all_groups[username_lower]['query_hits'].add(query)

                msg_info = {
                    'sender_id': sender_uid,
                    'sender_username': sender_username,
                    'sender_name': sender_name,
                    'text': (msg.message or '')[:200],
                    'date': str(msg.date),
                    'query': query,
                    'is_target_trader': is_target_trader,
                    'matched_trader': matched_trader
                }
                all_groups[username_lower]['messages_found'].append(msg_info)

                if is_target_trader:
                    all_groups[username_lower]['has_target_trader'] = True
                    all_groups[username_lower]['matched_traders'].add(matched_trader)

        except Exception as e:
            print(f"  Error: {e}")

        await asyncio.sleep(2)  # Rate limiting

    # Separate results
    verified_groups = {}
    unverified_groups = {}

    for uname, info in all_groups.items():
        info_copy = dict(info)
        info_copy['matched_traders'] = list(info['matched_traders'])
        info_copy['query_hits'] = list(info['query_hits'])

        if info['has_target_trader']:
            verified_groups[uname] = info_copy
        else:
            unverified_groups[uname] = info_copy

    print("\n" + "="*80)
    print("VERIFIED GROUPS (Target trader posted here):")
    print("="*80)
    if verified_groups:
        for uname, info in verified_groups.items():
            print(f"\n  @{info['username']} - {info['title']}")
            print(f"  Members: {info['participants_count']}")
            print(f"  Matched Traders: {info['matched_traders']}")
            print(f"  Query Hits: {info['query_hits']}")
            for m in info['messages_found']:
                if m['is_target_trader']:
                    print(f"    TRADER MSG by @{m['sender_username']} ({m['sender_name']}): {m['text'][:100]}")
    else:
        print("  No verified groups found.")

    print("\n" + "="*80)
    print(f"UNVERIFIED GROUPS (keyword match but no confirmed trader): {len(unverified_groups)}")
    print("="*80)
    for uname, info in unverified_groups.items():
        print(f"  @{info['username']} - {info['title']} ({info['participants_count']} members)")
        senders = set()
        for m in info['messages_found']:
            if m['sender_username']:
                senders.add(m['sender_username'])
        print(f"    Senders seen: {senders}")

    # Save results
    output = {
        'verified': verified_groups,
        'unverified': unverified_groups,
        'excluded_count': len(excluded),
        'queries_used': TRADER_QUERIES
    }
    # Convert sets for JSON
    for section in ['verified', 'unverified']:
        for k, v in output[section].items():
            if isinstance(v.get('matched_traders'), set):
                v['matched_traders'] = list(v['matched_traders'])
            if isinstance(v.get('query_hits'), set):
                v['query_hits'] = list(v['query_hits'])

    with open(r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\trader_search_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nResults saved to trader_search_results.json")
    print(f"Verified: {len(verified_groups)}, Unverified: {len(unverified_groups)}")

    await client.disconnect()

asyncio.run(main())
