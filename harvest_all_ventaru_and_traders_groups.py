import asyncio
import json
import os
import sys
from telethon import TelegramClient
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import InputPeerEmpty, InputMessagesFilterEmpty
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

SESSION_FILE = "froxy_session_output.txt"
with open(SESSION_FILE, "r", encoding="utf-8") as f:
    SESSION_STRING = f.read().strip()

# 1. Ventaru's unique phrases
VENTARU_PHRASES = [
    "Manus Ai 1 Hafta",
    "Grok Super Kişisel",
    "Duolingo Pro Mailinize",
    "ScreamingFrog 1 Yıl",
    "Hediye Kahve Coffy",
    "Tod 3 Ay Süper Dolu Paket",
    "Gemini Pro & Veo 3",
    "Perplexity Pro 1 Yıl 199",
    "Autodesk 1 Yıllık 349",
    "Storytel 1 Ay 69",
    "Gain 2 Ay Kod 80",
    "Exxen 3 Ay Reklamlı 130",
    "TV+ x HBO Max 1 Ay 80"
]

# 2. Other trader phrases (Food, Travel, Codes)
OTHER_TRADER_PHRASES = [
    "Getirfinansa davet kodum",
    "On mobile davet kodum",
    "Tıkla Gelsin 400",
    "Yemeksepeti 500/250",
    "Yemeksepeti 400/200",
    "Turna 600",
    "Turna 500",
    "Enuygun 500",
    "Migros 500/150",
    "Migros Sanal Market",
    "Pepsi 2.5L 2 TL",
    "Kazandırio 500 TL",
    "frebayt 1 gb",
    "TOD Sezonluk Süper Lig",
    "TOD Taraftar Paketi"
]

async def harvest_traders():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    
    with open("gruplar.txt", "r", encoding="utf-8", errors="ignore") as f:
        active_gruplar = {line.strip().lower().lstrip("@") for line in f if line.strip()}

    with open("blacklist.txt", "r", encoding="utf-8", errors="ignore") as f:
        blacklist = {line.strip().lower().lstrip("@") for line in f if line.strip()}

    all_queries = VENTARU_PHRASES + OTHER_TRADER_PHRASES
    print(f"Total phrases to query: {len(all_queries)}")

    discovered_chats = {}

    for q in all_queries:
        try:
            r = await client(SearchGlobalRequest(
                q=q,
                filter=InputMessagesFilterEmpty(),
                min_date=None, max_date=None, offset_rate=0,
                offset_peer=InputPeerEmpty(), offset_id=0, limit=50
            ))
            chat_map = {c.id: c for c in r.chats}
            new_in_query = 0
            for m in r.messages:
                peer = m.peer_id
                cid = getattr(peer, 'channel_id', None) or getattr(peer, 'chat_id', None)
                chat = chat_map.get(cid)
                if chat:
                    u = getattr(chat, 'username', None)
                    if u:
                        u_l = u.lower()
                        is_mega = getattr(chat, 'megagroup', False)
                        is_broad = getattr(chat, 'broadcast', False)
                        if is_mega and not is_broad:
                            if u_l not in discovered_chats:
                                discovered_chats[u_l] = {
                                    "username": u_l,
                                    "title": getattr(chat, 'title', ''),
                                    "matched_phrases": set(),
                                    "sample_messages": []
                                }
                                new_in_query += 1
                            discovered_chats[u_l]["matched_phrases"].add(q)
                            if m.message and len(discovered_chats[u_l]["sample_messages"]) < 2:
                                discovered_chats[u_l]["sample_messages"].append(m.message[:120].replace("\n", " "))
            print(f"Query '{q}': {len(r.messages)} msgs | Total discovered so far: {len(discovered_chats)}")
            await asyncio.sleep(0.8)
        except Exception as e:
            print(f"Query '{q}' err: {e}")

    print(f"\n==========================================")
    print(f"Total Trader-Active Groups Found: {len(discovered_chats)}")
    
    # Classify vs gruplar.txt & blacklist.txt
    new_found = []
    for u, data in discovered_chats.items():
        if u not in active_gruplar and u not in blacklist:
            data["matched_phrases"] = list(data["matched_phrases"])
            new_found.append(data)

    print(f"Completely NEW Trader Groups (Not in gruplar.txt / blacklist): {len(new_found)}")
    for item in new_found:
        print(f"  -> @{item['username']:<25} | {item['title'][:30]:<30} | {item['matched_phrases']}")

    with open("ventaru_and_traders_discovered.json", "w", encoding="utf-8") as f:
        json.dump(new_found, f, ensure_ascii=False, indent=2)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(harvest_traders())
