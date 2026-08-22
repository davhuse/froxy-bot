import asyncio
import json
import os
import re
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

# Target queries covering the requested traders and their peers
TARGET_QUERIES = [
    # Specific Traders mentioned by user
    "ventaru", "Ventaru", "craigkks", "John Snow", "Ferhat B47", "B47", "Cano31m", "cano31",
    
    # Trader signatures & Food/Coupon/Code/Ticket keywords
    "Yemeksepeti", "Yemek Sepeti", "Tikla Gelsin", "Tıkla Gelsin", "Migros Sanal", "Migros çek",
    "Turna bilet", "Turna 600", "Enuygun bilet", "Enuygun 500", "Pepsi 2.5", "Kazandırio",
    "frebayt", "Tod Süper Lig", "Tod Sezonluk", "Exxen 3 Ay", "Gain 2 Ay",
    "Chat Gpt Plus", "Canva Pro Sınırsız", "Windows 11 Pro", "Office 365",
    "kupon alım satım", "çek alım satım", "kod satış", "kod kupon", "kupon pazar",
    "hesap alım satım", "sosyal medya takipçi", "iban kadın erkek"
]

async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()

    with open("gruplar.txt", "r", encoding="utf-8", errors="ignore") as f:
        active_gruplar = {line.strip().lower().lstrip("@") for line in f if line.strip()}

    with open("blacklist.txt", "r", encoding="utf-8", errors="ignore") as f:
        blacklist = {line.strip().lower().lstrip("@") for line in f if line.strip()}

    print(f"Active in gruplar.txt: {len(active_gruplar)}")
    print(f"In blacklist.txt: {len(blacklist)}")
    print(f"Total search queries to run: {len(TARGET_QUERIES)}\n")

    discovered_groups = {} # username -> data

    for q in TARGET_QUERIES:
        try:
            r = await client(SearchGlobalRequest(
                q=q,
                filter=InputMessagesFilterEmpty(),
                min_date=None, max_date=None, offset_rate=0,
                offset_peer=InputPeerEmpty(), offset_id=0, limit=100
            ))
            chat_map = {c.id: c for c in r.chats}
            new_found = 0
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
                            if u_l not in discovered_groups:
                                discovered_groups[u_l] = {
                                    "username": u_l,
                                    "title": getattr(chat, 'title', ''),
                                    "matched_queries": set(),
                                    "sample_messages": []
                                }
                                new_found += 1
                            discovered_groups[u_l]["matched_queries"].add(q)
                            if m.message and len(discovered_groups[u_l]["sample_messages"]) < 3:
                                clean_txt = " ".join(m.message.split())
                                if len(clean_txt) > 120:
                                    clean_txt = clean_txt[:120] + "..."
                                if clean_txt not in discovered_groups[u_l]["sample_messages"]:
                                    discovered_groups[u_l]["sample_messages"].append(clean_txt)
            print(f"Query '{q:<24}' -> msgs: {len(r.messages):<3} | Total Groups Discovered: {len(discovered_groups)}")
            await asyncio.sleep(0.8)
        except Exception as e:
            print(f"Query '{q}' Error: {e}")

    print(f"\n=======================================================")
    print(f"TOTAL GROUPS DISCOVERED GLOBALLY: {len(discovered_groups)}")
    
    # Filter against existing list and blacklist
    unlisted_fresh = []
    for u, d in discovered_groups.items():
        d["matched_queries"] = list(d["matched_queries"])
        if u not in active_gruplar and u not in blacklist:
            unlisted_fresh.append(d)

    print(f"UNLISTED & FRESH TRADER GROUPS: {len(unlisted_fresh)}")
    print(f"=======================================================\n")

    for item in unlisted_fresh:
        print(f"  -> @{item['username']:<25} | {item['title'][:28]:<28} | Eşleşen: {item['matched_queries']}")

    with open("discovered_unlisted_trader_groups.json", "w", encoding="utf-8") as f:
        json.dump(unlisted_fresh, f, ensure_ascii=False, indent=2)

    with open("all_discovered_global_groups.json", "w", encoding="utf-8") as f:
        all_serial = {k: {**v, "matched_queries": list(v["matched_queries"])} for k, v in discovered_groups.items()}
        json.dump(all_serial, f, ensure_ascii=False, indent=2)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
