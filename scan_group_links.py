import asyncio
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityUrl, MessageEntityTextUrl

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def main():
    with open('froxy_session_output.txt', 'r', encoding='utf-8') as f:
        s_str = f.read().strip()
    client = TelegramClient(StringSession(s_str), API_ID, API_HASH)
    await client.connect()
    
    entity = await client.get_entity("gpt_nocard")
    print(f"Connected to {getattr(entity, 'title', 'gpt_nocard')}")

    # Let's collect all links posted in the last 15,000 messages
    link_messages = []
    all_domains = {}
    payshop_hits = []

    count = 0
    async for msg in client.iter_messages(entity, limit=15000):
        count += 1
        text = msg.text or ""
        
        # Check entities for URLs
        urls = []
        if msg.entities:
            for ent in msg.entities:
                if isinstance(ent, MessageEntityTextUrl):
                    urls.append(ent.url)
                elif isinstance(ent, MessageEntityUrl):
                    # extract from offset
                    offset = ent.offset
                    length = ent.length
                    urls.append(text[offset:offset+length])
        
        # Regex urls
        regex_urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+|[a-zA-Z0-9-]+\.(?:top|shop|xyz|com|cn|org|net|me|cc|io|site|vip|store|link)[^\s<>"]*', text)
        urls.extend(regex_urls)
        urls = list(set(urls))

        if 'payshop' in text.lower() or any('payshop' in u.lower() for u in urls):
            payshop_hits.append({
                'id': msg.id,
                'sender_id': msg.sender_id,
                'date': str(msg.date),
                'text': text,
                'urls': urls
            })
            print(f"\n[PAYSHOP HIT IN MESSAGE] Msg ID: {msg.id}, Sender: {msg.sender_id}")
            print(f"Text: {text}")

        if urls:
            link_messages.append({
                'id': msg.id,
                'sender_id': msg.sender_id,
                'date': str(msg.date),
                'text': text,
                'urls': urls
            })
            for u in urls:
                domain = re.findall(r'https?://([^/]+)|www\.([^/]+)', u)
                d_str = (domain[0][0] or domain[0][1]) if domain else u[:30]
                all_domains[d_str] = all_domains.get(d_str, 0) + 1

        if count % 2000 == 0:
            print(f"Scanned {count} messages... Found {len(link_messages)} link messages, {len(payshop_hits)} payshop hits.")

    print(f"\n================ SUMMARY ================")
    print(f"Total Messages Scanned: {count}")
    print(f"Total Link Messages: {len(link_messages)}")
    print(f"Total Payshop Hits: {len(payshop_hits)}")
    print(f"\nTop Domains in group:")
    for d, c in sorted(all_domains.items(), key=lambda x: x[1], reverse=True)[:30]:
        print(f"  {d}: {c} times")

    with open('group_links_analysis.json', 'w', encoding='utf-8') as f:
        json.dump({
            'payshop_hits': payshop_hits,
            'top_domains': all_domains,
            'recent_link_messages': link_messages[:100]
        }, f, ensure_ascii=False, indent=2)

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
