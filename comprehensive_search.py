"""
COMPREHENSIVE trader group finder:
1. Paginate through ALL SearchGlobalRequest results (not just first 100)
2. Use multiple sessions (froxy, lisans, keyvadi)
3. Search with trader-specific ad phrases
4. Use GetCommonChatsRequest to find shared groups with traders
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import asyncio
import json
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import SearchGlobalRequest, GetCommonChatsRequest
from telethon.tl.types import InputMessagesFilterEmpty, InputPeerEmpty, InputUser

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

# Load sessions
SESSIONS = {}
for name, path in [
    ("froxy", r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\froxy_session_output.txt"),
    ("lisans", r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\lisans_session_output.txt"),
    ("keyvadi", r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\session_key_output.txt"),
]:
    with open(path, "r") as f:
        SESSIONS[name] = f.read().strip()

# Load exclusion lists
excluded = set()
with open(r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\gruplar.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip().lower()
        if line: excluded.add(line)
with open(r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\blacklist.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip().lower()
        if line and not line.startswith("-"): excluded.add(line)

print(f"Excluded: {len(excluded)} groups")

# Known trader IDs (from debug results)
TRADER_IDS = {
    7738823680: "AuraDijital",
    1553279766: "Ventaru1234567890",
}
TRADER_USERNAMES = {'auradijital', 'cano31m', 'ventaru1234567890', 'ferhatbey47', 'craigkks'}

# Search queries - trader usernames + distinctive ad phrases
QUERIES = [
    # Exact usernames with @
    "@AuraDijital", "@Cano31m", "@Ventaru1234567890", "@Ferhatbey47",
    # Distinctive ad phrases from AuraDijital
    "Dijital dünyanın anahtarı",
    "+800 REFERANS",
    # Distinctive ad phrases from Ventaru
    "PREMİUM HİZMETLER",
    "Chat Gpt Plus 1 Ay Kişisel",
    "Canva Pro Kişisel",
    "Netflix Premium",
    # More generic trader phrases
    "kupon kod satış",
    "hesap satış garantili",
    "dijital lisans",
]

async def paginated_search(client, query, max_pages=5):
    """Search with pagination to get more than 100 results."""
    all_messages = []
    all_chats = {}
    all_users = {}
    
    offset_rate = 0
    offset_peer = InputPeerEmpty()
    offset_id = 0
    
    for page in range(max_pages):
        try:
            result = await client(SearchGlobalRequest(
                q=query,
                filter=InputMessagesFilterEmpty(),
                min_date=None, max_date=None,
                offset_rate=offset_rate,
                offset_peer=offset_peer,
                offset_id=offset_id,
                limit=100
            ))
            
            if not result.messages:
                break
            
            for c in result.chats:
                all_chats[c.id] = c
            for u in result.users:
                all_users[u.id] = u
            all_messages.extend(result.messages)
            
            # Set pagination offsets
            last_msg = result.messages[-1]
            offset_rate = getattr(last_msg, 'date', None)
            if offset_rate:
                import time
                offset_rate = int(offset_rate.timestamp())
            else:
                offset_rate = 0
            offset_id = last_msg.id
            
            # Get the peer for offset
            if hasattr(last_msg.peer_id, 'channel_id'):
                from telethon.tl.types import InputPeerChannel
                cid = last_msg.peer_id.channel_id
                chat = all_chats.get(cid)
                if chat:
                    access_hash = getattr(chat, 'access_hash', 0) or 0
                    offset_peer = InputPeerChannel(cid, access_hash)
                else:
                    break
            else:
                break
            
            if len(result.messages) < 100:
                break  # No more results
            
            await asyncio.sleep(1.5)
            
        except Exception as e:
            print(f"    Page {page+1} error: {e}")
            break
    
    return all_messages, all_chats, all_users


async def search_with_session(session_name, session_string):
    """Run all searches with a single session."""
    print(f"\n{'='*80}")
    print(f"SESSION: {session_name}")
    print(f"{'='*80}")
    
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.start()
        me = await client.get_me()
        print(f"Connected as: {me.first_name} (ID: {me.id})")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return {}
    
    # Track groups: {username_lower: {info}}
    session_groups = {}
    
    for query in QUERIES:
        print(f"\n  --- Query: '{query}' ---")
        messages, chats, users = await paginated_search(client, query, max_pages=3)
        print(f"    Total: {len(messages)} msgs, {len(chats)} chats")
        
        for msg in messages:
            if hasattr(msg.peer_id, 'channel_id'):
                chat_id = msg.peer_id.channel_id
            elif hasattr(msg.peer_id, 'chat_id'):
                chat_id = msg.peer_id.chat_id
            else:
                continue
            
            chat = chats.get(chat_id)
            if not chat:
                continue
            
            mega = getattr(chat, 'megagroup', False)
            bcast = getattr(chat, 'broadcast', False)
            if not mega or bcast:
                continue
            
            username = getattr(chat, 'username', None)
            if not username:
                continue
            
            uname_lower = username.lower()
            if uname_lower in excluded:
                continue
            
            # Get sender
            sender_uid = None
            if hasattr(msg, 'from_id') and msg.from_id:
                if hasattr(msg.from_id, 'user_id'):
                    sender_uid = msg.from_id.user_id
            
            sender_uname = None
            sender_name = None
            if sender_uid and sender_uid in users:
                u = users[sender_uid]
                sender_uname = getattr(u, 'username', None)
                first = getattr(u, 'first_name', '') or ''
                last = getattr(u, 'last_name', '') or ''
                sender_name = f"{first} {last}".strip()
            
            is_trader = False
            matched_trader = None
            if sender_uname and sender_uname.lower() in TRADER_USERNAMES:
                is_trader = True
                matched_trader = sender_uname
            elif sender_uid in TRADER_IDS:
                is_trader = True
                matched_trader = TRADER_IDS[sender_uid]
            
            if uname_lower not in session_groups:
                session_groups[uname_lower] = {
                    'username': username,
                    'title': getattr(chat, 'title', ''),
                    'members': getattr(chat, 'participants_count', None),
                    'has_trader': False,
                    'traders_found': set(),
                    'queries': set(),
                    'sample_messages': [],
                    'all_senders': set()
                }
            
            g = session_groups[uname_lower]
            g['queries'].add(query)
            if sender_uname:
                g['all_senders'].add(sender_uname)
            
            if is_trader:
                g['has_trader'] = True
                g['traders_found'].add(matched_trader)
                if len(g['sample_messages']) < 5:
                    g['sample_messages'].append({
                        'sender': matched_trader,
                        'text': (msg.message or '')[:200],
                        'date': str(msg.date)
                    })
        
        await asyncio.sleep(2)
    
    # Also try GetCommonChatsRequest with known trader IDs
    print(f"\n  --- GetCommonChats with trader IDs ---")
    for trader_id, trader_name in TRADER_IDS.items():
        try:
            # We need InputUser which requires access_hash
            # Try to find it from already-seen users
            from telethon.tl.functions.users import GetUsersRequest
            from telethon.tl.types import InputUser as IU
            
            # Search for the trader to get their access_hash
            # Use a dummy search to find them
            for q in [f"@{trader_name}"]:
                r = await client(SearchGlobalRequest(
                    q=q, filter=InputMessagesFilterEmpty(),
                    min_date=None, max_date=None,
                    offset_rate=0, offset_peer=InputPeerEmpty(),
                    offset_id=0, limit=10
                ))
                for u in r.users:
                    if u.id == trader_id:
                        ah = getattr(u, 'access_hash', 0) or 0
                        common = await client(GetCommonChatsRequest(
                            user_id=IU(trader_id, ah),
                            max_id=0,
                            limit=100
                        ))
                        print(f"    {trader_name}: {len(common.chats)} common chats")
                        for c in common.chats:
                            uname = getattr(c, 'username', None)
                            title = getattr(c, 'title', '')
                            mega = getattr(c, 'megagroup', False)
                            if uname and mega:
                                ul = uname.lower()
                                in_excluded = ul in excluded
                                tag = "EXCLUDED" if in_excluded else "**NEW**"
                                print(f"      [{tag}] @{uname} - {title}")
                                if not in_excluded:
                                    if ul not in session_groups:
                                        session_groups[ul] = {
                                            'username': uname,
                                            'title': title,
                                            'members': getattr(c, 'participants_count', None),
                                            'has_trader': True,
                                            'traders_found': {trader_name},
                                            'queries': {'GetCommonChats'},
                                            'sample_messages': [],
                                            'all_senders': set()
                                        }
                                    else:
                                        session_groups[ul]['has_trader'] = True
                                        session_groups[ul]['traders_found'].add(trader_name)
                        break
                await asyncio.sleep(2)
        except Exception as e:
            print(f"    {trader_name} error: {e}")
    
    await client.disconnect()
    return session_groups


async def main():
    all_new_groups = {}  # Across all sessions
    
    for name, sess_str in SESSIONS.items():
        groups = await search_with_session(name, sess_str)
        for uname, info in groups.items():
            if uname not in all_new_groups:
                all_new_groups[uname] = info
            else:
                # Merge
                existing = all_new_groups[uname]
                existing['has_trader'] = existing['has_trader'] or info['has_trader']
                existing['traders_found'] |= info['traders_found']
                existing['queries'] |= info['queries']
                existing['all_senders'] |= info['all_senders']
                existing['sample_messages'].extend(info['sample_messages'])
    
    # Final report
    print(f"\n{'='*80}")
    print("FINAL RESULTS - ALL SESSIONS COMBINED")
    print(f"{'='*80}")
    
    verified = {k: v for k, v in all_new_groups.items() if v['has_trader']}
    unverified = {k: v for k, v in all_new_groups.items() if not v['has_trader']}
    
    print(f"\n✅ VERIFIED NEW GROUPS (trader posted here): {len(verified)}")
    for uname, info in verified.items():
        print(f"\n  @{info['username']} - {info['title']}")
        print(f"    Members: {info['members']}")
        print(f"    Traders: {info['traders_found']}")
        print(f"    Queries: {info['queries']}")
        for m in info['sample_messages'][:3]:
            print(f"    MSG [{m['sender']}]: {m['text'][:100]}")
    
    print(f"\n⚠️ UNVERIFIED NEW GROUPS (keyword match, no trader confirmed): {len(unverified)}")
    for uname, info in unverified.items():
        print(f"  @{info['username']} - {info['title']} (members: {info['members']})")
        print(f"    Senders: {info['all_senders']}")
        print(f"    Queries: {info['queries']}")
    
    # Save
    output = {}
    for k, v in all_new_groups.items():
        vc = dict(v)
        vc['traders_found'] = list(v['traders_found'])
        vc['queries'] = list(v['queries'])
        vc['all_senders'] = list(v['all_senders'])
        output[k] = vc
    
    with open(r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\comprehensive_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\nSaved to comprehensive_results.json")

asyncio.run(main())
