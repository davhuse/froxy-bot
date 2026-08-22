import asyncio
import json
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

async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()

    with open("gruplar.txt", "r", encoding="utf-8", errors="ignore") as f:
        active_gruplar = {line.strip().lower().lstrip("@") for line in f if line.strip()}

    with open("blacklist.txt", "r", encoding="utf-8", errors="ignore") as f:
        blacklist = {line.strip().lower().lstrip("@") for line in f if line.strip()}

    # 1. Fetch live messages from known accessible seed groups
    accessible_seeds = ["kuponkodalimsatimm", "kodkuponmarketi", "indirimcek", "indirim363", "mukyemek"]
    
    unique_ad_phrases = set()
    seller_usernames = set()

    for s in accessible_seeds:
        try:
            entity = await client.get_entity(s)
            msgs = await client.get_messages(entity, limit=200)
            print(f"Scanned {len(msgs)} messages in @{s}")
            for m in msgs:
                if not m or not m.text:
                    continue
                txt = m.text.strip()
                
                # Extract usernames in ads
                for found_u in re.finditer(r"@([a-zA-Z0-9_]{5,32})", txt):
                    u_cand = found_u.group(1).lower()
                    if u_cand not in {"admin", "destek", "bot", "yardim", "iletisim", "guvence", "referans"}:
                        seller_usernames.add(u_cand)

                # Extract distinctive multi-word ad slogans (6-12 words)
                lines = [l.strip() for l in txt.split("\n") if len(l.strip()) > 25 and len(l.strip()) < 80]
                for l in lines[:2]:
                    # clean emojis/symbols
                    clean_l = re.sub(r'[^\w\s\d]', '', l).strip()
                    if len(clean_l.split()) >= 4:
                        unique_ad_phrases.add(clean_l[:45])
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Error @{s}: {e}")

    print(f"\nUnique Seller Usernames Found in Live Ads: {len(seller_usernames)}")
    print(f"Unique Distinctive Ad Phrases Found: {len(unique_ad_phrases)}")

    # 2. Search Telegram Global Messages for all seller usernames and ad phrases
    all_targets = list(seller_usernames)[:30] + list(unique_ad_phrases)[:30]
    discovered_new_groups = {}

    print(f"\nSearching Telegram Global for {len(all_targets)} seller signatures...")
    for q in all_targets:
        try:
            r = await client(SearchGlobalRequest(
                q=q,
                filter=InputMessagesFilterEmpty(),
                min_date=None, max_date=None, offset_rate=0,
                offset_peer=InputPeerEmpty(), offset_id=0, limit=40
            ))
            chat_map = {c.id: c for c in r.chats}
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
                            if u_l not in active_gruplar and u_l not in blacklist:
                                if u_l not in discovered_new_groups:
                                    discovered_new_groups[u_l] = {
                                        "username": u_l,
                                        "title": getattr(chat, 'title', ''),
                                        "matched_sellers_or_ads": set(),
                                        "sample_messages": []
                                    }
                                discovered_new_groups[u_l]["matched_sellers_or_ads"].add(q)
                                if m.message and len(discovered_new_groups[u_l]["sample_messages"]) < 2:
                                    discovered_new_groups[u_l]["sample_messages"].append(m.message[:110].replace("\n", " "))
            print(f"Query '{q[:25]}': {len(r.messages)} msgs | New Unlisted Groups Found: {len(discovered_new_groups)}")
            await asyncio.sleep(0.7)
        except Exception as e:
            print(f"Query err '{q[:20]}': {e}")

    print(f"\n=======================================================")
    print(f"🎉 TOPLAM YENİ VE LİSTELERDE OLMAYAN TÜCCAR GRUPLARI: {len(discovered_new_groups)}")
    print(f"=======================================================\n")

    serializable = []
    for u, data in discovered_new_groups.items():
        data["matched_sellers_or_ads"] = list(data["matched_sellers_or_ads"])
        serializable.append(data)
        print(f"  -> @{u:<25} | {data['title'][:28]:<28} | Eşleşen: {data['matched_sellers_or_ads']}")

    with open("fresh_unlisted_trader_groups.json", "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
