import asyncio
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import MessageEntityUrl, MessageEntityTextUrl

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

def extract_urls(text, entities=None):
    urls = []
    if entities:
        for ent in entities:
            if isinstance(ent, MessageEntityTextUrl):
                urls.append(ent.url)
            elif isinstance(ent, MessageEntityUrl) and text:
                offset = ent.offset
                length = ent.length
                urls.append(text[offset:offset+length])
    
    # Regex fallback
    if text:
        regex_urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+|[a-zA-Z0-9-]+\.(?:top|shop|xyz|com|cn|org|net|me|cc|io|site|vip|store|link|cc|app|work|dev)[^\s<>"]*', text)
        urls.extend(regex_urls)

    # Clean & filter out telegram links (t.me, telegram.me, etc.)
    clean_urls = []
    for u in urls:
        u_clean = u.strip('.,;!()[]{}<>"\'')
        if not u_clean.startswith('http://') and not u_clean.startswith('https://'):
            u_clean = 'https://' + u_clean
        # Exclude telegram channels/links
        if 't.me' in u_clean.lower() or 'telegram.me' in u_clean.lower() or 'telegram.org' in u_clean.lower():
            continue
        clean_urls.append(u_clean)
    return list(set(clean_urls))

async def main():
    client = await get_working_client()
    if not client:
        print("No authorized session!")
        return

    entity = await client.get_entity("gpt_nocard")
    print(f"Scanning group: {getattr(entity, 'title', 'gpt_nocard')}")

    # Search terms for Gemini & Pay / Shops
    gemini_terms = ['gemini', 'Gemini', 'GEMINI', '双子座', '18 months', '18 month', '18m', '18b']
    all_gemini_msgs = {}

    for term in ['gemini', '双子座', '18m', 'pay', 'shop', 'faka', '卡网', '发卡', '购买', '下单']:
        print(f"Searching term: '{term}'...")
        try:
            async for msg in client.iter_messages(entity, search=term, limit=400):
                if msg and msg.text:
                    all_gemini_msgs[msg.id] = msg
        except Exception as e:
            print(f"Search error {term}: {e}")

    # Also iterate latest 3000 messages
    print("Fetching recent message stream...")
    async for msg in client.iter_messages(entity, limit=3000):
        if msg and msg.text:
            all_gemini_msgs[msg.id] = msg

    print(f"Total unique messages collected: {len(all_gemini_msgs)}")

    # Filter messages mentioning Gemini
    gemini_posts = []
    user_ids = set()

    for mid, msg in all_gemini_msgs.items():
        text = msg.text or ""
        lower = text.lower()
        if any(t.lower() in lower for t in ['gemini', '双子座']) or ('18' in lower and ('month' in lower or 'ay' in lower or 'pro' in lower or 'link' in lower)):
            urls = extract_urls(text, msg.entities)
            sender = msg.sender
            sid = msg.sender_id
            if sid:
                user_ids.add(sid)
            gemini_posts.append({
                'msg_id': mid,
                'sender_id': sid,
                'sender': sender,
                'date': str(msg.date),
                'text': text,
                'urls': urls
            })

    print(f"Found {len(gemini_posts)} Gemini messages across {len(user_ids)} users.")

    # Now let's fetch user bios for these users to extract any web pay/shop links in bio
    user_bios = {}
    for uid in user_ids:
        try:
            u_entity = await client.get_entity(uid)
            full = await client(GetFullUserRequest(u_entity))
            bio = ""
            if hasattr(full, 'full_user') and hasattr(full.full_user, 'about'):
                bio = full.full_user.about or ""
            elif hasattr(full, 'about'):
                bio = full.about or ""
            
            bio_urls = extract_urls(bio)
            username = getattr(u_entity, 'username', '') or ''
            first_name = getattr(u_entity, 'first_name', '') or ''
            last_name = getattr(u_entity, 'last_name', '') or ''
            
            user_bios[uid] = {
                'name': f"{first_name} {last_name}".strip(),
                'username': f"@{username}" if username else "Yok",
                'bio': bio,
                'bio_urls': bio_urls
            }
            await asyncio.sleep(0.1)
        except Exception:
            user_bios[uid] = {
                'name': f"User_{uid}",
                'username': "Yok",
                'bio': "",
                'bio_urls': []
            }

    # Compile results with web pay/shop links
    results_with_pay_links = []
    for post in gemini_posts:
        uid = post['sender_id']
        u_info = user_bios.get(uid, {})
        
        all_pay_links = list(set(post['urls'] + u_info.get('bio_urls', [])))
        
        # If there are direct web links (not telegram channels)
        if all_pay_links:
            results_with_pay_links.append({
                'msg_id': post['msg_id'],
                'date': post['date'],
                'user_name': u_info.get('name', ''),
                'username': u_info.get('username', ''),
                'user_id': uid,
                'pay_links': all_pay_links,
                'bio': u_info.get('bio', ''),
                'message_text': post['text']
            })

    print(f"\n================ GEMINI PAY LINK RESULTS ================")
    print(f"Total Gemini Ads with Pay Links: {len(results_with_pay_links)}")
    
    unique_links = {}
    for r in results_with_pay_links:
        for l in r['pay_links']:
            if l not in unique_links:
                unique_links[l] = []
            unique_links[l].append(r)

    print(f"Unique Payment / Store URLs Found: {len(unique_links)}")
    for l, items in unique_links.items():
        sample = items[0]
        print(f"\n[PAY LINK]: {l}")
        print(f"Satıcı: {sample['user_name']} ({sample['username']}) - ID: {sample['user_id']}")
        print(f"İlan Metni: {sample['message_text'][:120]}...")
        if sample['bio']:
            print(f"Biyo: {sample['bio']}")

    # Save to json
    with open('gemini_pay_links.json', 'w', encoding='utf-8') as f:
        json.dump({
            'unique_links_count': len(unique_links),
            'unique_links': list(unique_links.keys()),
            'detailed_results': results_with_pay_links
        }, f, ensure_ascii=False, indent=2)

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
