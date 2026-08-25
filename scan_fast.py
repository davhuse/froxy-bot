import asyncio
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def get_working_client():
    sessions = ['froxy_session_output.txt', 'session_7384.txt', 'session_key_output.txt', 'lisans_session_output.txt']
    for s_file in sessions:
        try:
            with open(s_file, 'r', encoding='utf-8') as f:
                s_str = f.read().strip()
            if not s_str:
                continue
            client = TelegramClient(StringSession(s_str), API_ID, API_HASH)
            await client.connect()
            if await client.is_user_authorized():
                return client
            else:
                await client.disconnect()
        except Exception:
            pass
    return None

async def main():
    client = await get_working_client()
    if not client:
        print("No authorized session found!", flush=True)
        return

    entity = await client.get_entity("gpt_nocard")
    print(f"Group: {getattr(entity, 'title', 'gpt_nocard')} (@{getattr(entity, 'username', 'gpt_nocard')})", flush=True)

    # 1. Search messages by keywords
    keywords = ['netflix', 'payshop', '奈飞', '网飞', 'shop']
    all_relevant_msgs = {}

    for kw in keywords:
        print(f"Searching server-side for '{kw}'...", flush=True)
        try:
            async for msg in client.iter_messages(entity, search=kw, limit=200):
                if msg and msg.text:
                    all_relevant_msgs[msg.id] = msg
        except Exception as e:
            print(f"Search error for {kw}: {e}", flush=True)

    # 2. Also fetch latest 1000 messages
    print("Fetching latest 1000 messages...", flush=True)
    async for msg in client.iter_messages(entity, limit=1000):
        if msg and msg.text:
            all_relevant_msgs[msg.id] = msg

    print(f"Total collected messages to analyze: {len(all_relevant_msgs)}", flush=True)

    # Group by sender
    user_msg_map = {}
    for mid, msg in all_relevant_msgs.items():
        sid = msg.sender_id
        if not sid:
            continue
        if sid not in user_msg_map:
            user_msg_map[sid] = {
                'sender': msg.sender,
                'messages': []
            }
        user_msg_map[sid]['messages'].append(msg)

    print(f"Unique senders found: {len(user_msg_map)}", flush=True)

    # Check which users mention netflix or shop/payshop
    candidate_users = {}
    for sid, data in user_msg_map.items():
        all_text = " ".join([(m.text or "") for m in data['messages']]).lower()
        has_netflix = any(k in all_text for k in ['netflix', '奈飞', '网飞', 'nf'])
        has_shop = any(k in all_text for k in ['payshop', 'shop', 'http', '.com', '.xyz', '.top', '发卡', '自动发卡', '独享', '拼车', '账号'])
        
        if has_netflix or has_shop:
            candidate_users[sid] = data

    print(f"Candidate users with relevant terms: {len(candidate_users)}", flush=True)

    # Now inspect profiles / bios of candidates
    matched_sellers = []
    
    for sid, data in candidate_users.items():
        sender = data['sender']
        try:
            if not sender:
                sender = await client.get_entity(sid)
        except Exception:
            continue

        username = getattr(sender, 'username', '') or ''
        first_name = getattr(sender, 'first_name', '') or ''
        last_name = getattr(sender, 'last_name', '') or ''
        full_name = f"{first_name} {last_name}".strip()

        # Get Bio
        bio = ""
        try:
            full = await client(GetFullUserRequest(sender))
            if hasattr(full, 'full_user') and hasattr(full.full_user, 'about'):
                bio = full.full_user.about or ""
            elif hasattr(full, 'about'):
                bio = full.about or ""
        except Exception:
            bio = ""

        # Extract links from bio and messages
        combined_text = bio + "\n" + "\n".join([(m.text or "") for m in data['messages']])
        combined_lower = combined_text.lower()

        # Check for payshop specifically
        payshop_links = re.findall(r'https?://[^\s<>"]*payshop[^\s<>"]*|[a-zA-Z0-9-]*payshop[a-zA-Z0-9-.]*', combined_text, re.IGNORECASE)
        all_links = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+|[a-zA-Z0-9-]+\.(?:top|shop|xyz|com|cn|org|net|me|cc|io|site|vip|store|link)[^\s<>"]*', combined_text)

        is_netflix_related = any(k in combined_lower for k in ['netflix', '奈飞', '网飞', 'nf '])
        is_payshop_related = ('payshop' in combined_lower) or (len(payshop_links) > 0)
        
        # Check if they sell netflix and have ANY shop link or payshop link
        if is_netflix_related:
            matched_sellers.append({
                'id': sid,
                'name': full_name,
                'username': f"@{username}" if username else "Yok",
                'bio': bio,
                'is_payshop': is_payshop_related,
                'payshop_links': list(set(payshop_links)),
                'all_links': list(set(all_links)),
                'sample_messages': [m.text for m in data['messages'][:3] if m.text]
            })

    print(f"\n================ RESULTS ================", flush=True)
    payshop_only = [s for s in matched_sellers if s['is_payshop']]
    print(f"Netflix Sellers with PAYSHOP link/mention: {len(payshop_only)}", flush=True)
    for p in payshop_only:
        print(f"\n[PAYSHOP NETFLIX SELLER]")
        print(f"Kullanıcı: {p['name']} ({p['username']}) - ID: {p['id']}")
        print(f"Biyo (About): {p['bio']}")
        print(f"Payshop Linkleri: {p['payshop_links']}")
        print(f"Örnek Mesaj: {p['sample_messages'][0] if p['sample_messages'] else 'Yok'}")

    print(f"\n--- Other Netflix Sellers (All Platforms) ---", flush=True)
    other_sellers = [s for s in matched_sellers if not s['is_payshop']]
    for o in other_sellers:
        print(f"\n[OTHER NETFLIX SELLER]")
        print(f"Kullanıcı: {o['name']} ({o['username']}) - ID: {o['id']}")
        print(f"Biyo (About): {o['bio']}")
        print(f"Tüm Linkler: {o['all_links']}")
        print(f"Örnek Mesaj: {o['sample_messages'][0] if o['sample_messages'] else 'Yok'}")

    with open('final_netflix_sellers.json', 'w', encoding='utf-8') as f:
        json.dump({
            'payshop_sellers': payshop_only,
            'other_netflix_sellers': other_sellers
        }, f, ensure_ascii=False, indent=2)

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
