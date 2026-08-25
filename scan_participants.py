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
    with open('froxy_session_output.txt', 'r', encoding='utf-8') as f:
        s_str = f.read().strip()
    client = TelegramClient(StringSession(s_str), API_ID, API_HASH)
    await client.connect()
    return client

async def main():
    client = await get_working_client()
    entity = await client.get_entity("gpt_nocard")
    print(f"Connected to: {getattr(entity, 'title', 'gpt_nocard')}")

    print("Fetching group participants...")
    participants = []
    try:
        async for user in client.iter_participants(entity, limit=3000):
            participants.append(user)
    except Exception as e:
        print(f"Error fetching participants: {e}")

    print(f"Total participants fetched: {len(participants)}")

    # We will inspect bios and user info for all participants
    payshop_matches = []
    netflix_sellers = []

    count = 0
    for user in participants:
        count += 1
        username = getattr(user, 'username', '') or ''
        first_name = getattr(user, 'first_name', '') or ''
        last_name = getattr(user, 'last_name', '') or ''
        full_name = f"{first_name} {last_name}".strip()

        # Get full profile (bio/about)
        bio = ""
        try:
            full = await client(GetFullUserRequest(user))
            if hasattr(full, 'full_user') and hasattr(full.full_user, 'about'):
                bio = full.full_user.about or ""
            elif hasattr(full, 'about'):
                bio = full.about or ""
        except Exception as e:
            # If rate limited or error, continue
            pass

        bio_lower = bio.lower()
        has_payshop = 'payshop' in bio_lower or 'payshop' in username.lower() or 'payshop' in full_name.lower()
        has_netflix = any(k in bio_lower for k in ['netflix', '奈飞', '网飞']) or any(k in full_name.lower() for k in ['netflix', '奈飞', '网飞'])

        # Find any shop / payment links in bio
        links = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+|[a-zA-Z0-9-]+\.(?:top|shop|xyz|com|cn|org|net|me|cc|io|site|vip|store|link)[^\s<>"]*', bio)
        telegram_bots = re.findall(r'@[a-zA-Z0-9_]+(?:bot|store|shop)', bio, re.IGNORECASE)

        if has_payshop:
            item = {
                'id': user.id,
                'name': full_name,
                'username': f"@{username}" if username else "Yok",
                'bio': bio,
                'links': links,
                'bots': telegram_bots,
                'has_netflix_in_bio': has_netflix
            }
            payshop_matches.append(item)
            print(f"\n[FOUND PAYSHOP USER IN BIO/NAME!]")
            print(f"Kullanıcı: {full_name} (@{username}) | ID: {user.id}")
            print(f"Bio: {bio}")
            print(f"Linkler: {links}")

        if has_netflix:
            netflix_sellers.append({
                'id': user.id,
                'name': full_name,
                'username': f"@{username}" if username else "Yok",
                'bio': bio,
                'links': links,
                'bots': telegram_bots,
                'has_payshop': has_payshop
            })

        if count % 100 == 0:
            print(f"Processed {count}/{len(participants)} users... (Payshop matches so far: {len(payshop_matches)})", flush=True)

    print(f"\n================ SUMMARY ================")
    print(f"Total Participants Scanned: {count}")
    print(f"Payshop Matches: {len(payshop_matches)}")
    print(f"Netflix Bio Sellers: {len(netflix_sellers)}")

    with open('participant_scan_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'payshop_matches': payshop_matches,
            'netflix_sellers': netflix_sellers
        }, f, ensure_ascii=False, indent=2)

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
