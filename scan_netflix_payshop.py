import asyncio
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.users import GetFullUserRequest

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
        print("No authorized session found!")
        return

    entity = await client.get_entity("gpt_nocard")
    print(f"Connected to group: {getattr(entity, 'title', 'gpt_nocard')}")

    # We will map sender_id -> {sender_obj, messages, netflix_count, links}
    senders = {}
    total_msgs = 0

    print("Fetching last 8000 messages...")
    async for msg in client.iter_messages(entity, limit=8000):
        total_msgs += 1
        if not msg.text:
            continue
        
        sender = await msg.get_sender()
        if not sender:
            continue

        sid = sender.id
        if sid not in senders:
            senders[sid] = {
                'user': sender,
                'messages': [],
                'netflix_msgs': [],
                'all_links': set()
            }
        
        text = msg.text
        lower = text.lower()

        # Find URLs
        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+|[a-zA-Z0-9-]+\.(?:top|shop|xyz|com|cn|org|net|me|cc|io|site|vip|store|link)[^\s<>"]*', text)
        for u in urls:
            senders[sid]['all_links'].add(u)

        if 'netflix' in lower or '奈飞' in text or '网飞' in text or 'nf' in lower.split():
            senders[sid]['netflix_msgs'].append({
                'id': msg.id,
                'date': str(msg.date),
                'text': text
            })
        
        senders[sid]['messages'].append({
            'id': msg.id,
            'date': str(msg.date),
            'text': text
        })

    print(f"Scanned {total_msgs} messages from {len(senders)} unique users.")
    
    # Filter users who sent Netflix / 奈飞 / 网飞 messages OR have links
    netflix_users = [s for s in senders.values() if len(s['netflix_msgs']) > 0]
    print(f"Users mentioning Netflix: {len(netflix_users)}")

    results = []
    for sdata in netflix_users:
        user = sdata['user']
        username = getattr(user, 'username', None) or "NoUsername"
        first_name = getattr(user, 'first_name', '') or ''
        last_name = getattr(user, 'last_name', '') or ''
        full_name = f"{first_name} {last_name}".strip()
        
        bio = ""
        try:
            full = await client(GetFullUserRequest(user))
            # In telethon, full is UserFull object containing full_user
            if hasattr(full, 'full_user') and hasattr(full.full_user, 'about'):
                bio = full.full_user.about or ""
            elif hasattr(full, 'about'):
                bio = full.about or ""
        except Exception as e:
            bio = f"Error fetching bio: {e}"

        bio_links = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+|[a-zA-Z0-9-]+\.(?:top|shop|xyz|com|cn|org|net|me|cc|io|site|vip|store|link)[^\s<>"]*', bio)

        # Check if payshop is present anywhere
        has_payshop_in_bio = 'payshop' in bio.lower()
        has_payshop_in_links = any('payshop' in l.lower() for l in sdata['all_links'])
        has_payshop_in_text = any('payshop' in m['text'].lower() for m in sdata['messages'])
        
        user_info = {
            'id': user.id,
            'name': full_name,
            'username': username,
            'bio': bio,
            'bio_links': bio_links,
            'message_links': list(sdata['all_links']),
            'has_payshop': has_payshop_in_bio or has_payshop_in_links or has_payshop_in_text,
            'netflix_msgs_count': len(sdata['netflix_msgs']),
            'sample_netflix_msg': sdata['netflix_msgs'][0]['text'] if sdata['netflix_msgs'] else "",
            'sample_msgs': [m['text'] for m in sdata['messages'][:3]]
        }
        results.append(user_info)
        await asyncio.sleep(0.1)

    print("\n--- Summary of all Netflix sellers/mentioners ---")
    payshop_matches = []
    for r in results:
        print(f"\nUser: {r['name']} (@{r['username']}) [ID: {r['id']}]")
        print(f"Bio: {r['bio']}")
        print(f"Bio Links: {r['bio_links']}")
        print(f"Message Links: {r['message_links']}")
        print(f"Netflix msg count: {r['netflix_msgs_count']}")
        print(f"Sample msg: {r['sample_netflix_msg'][:100]}...")
        if r['has_payshop'] or any('payshop' in str(l).lower() for l in r['bio_links'] + r['message_links']):
            payshop_matches.append(r)

    print(f"\n>>> Payshop specific matches: {len(payshop_matches)} <<<")
    with open('all_netflix_users.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
