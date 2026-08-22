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

# 1. Load EXHAUSTIVE blacklist & target exclusions (1,470 entries)
with open("exhaustive_excluded_groups.json", "r", encoding="utf-8") as f:
    EXCLUDED_SET = set(json.load(f))

print(f"[*] Toplam Kesin Yasaklı / Mevcut Grup Sayısı: {len(EXCLUDED_SET)}")

# 2. Comprehensive trader keywords and product inventories
SEARCH_QUERIES = [
    # Named Traders & variations
    "ventaru", "Ventaru", "craigkks", "John Snow", "Ferhat B47", "B47", "cano31m", "Cano31", "cano31m",
    
    # Ventaru's specific unique copy-paste inventory
    "Manus Ai 1 Hafta", "Grok Super Kişisel", "Duolingo Pro Mailinize Tanımlanır",
    "ScreamingFrog 1 Yıl", "Autodesk 1 Yıllık", "Tod 3 Ay Süper Dolu Paket",
    "Perplexity Pro 1 Yıl", "Gemini Pro & Veo 3", "TV+ x HBO Max 1 Ay 80",
    "Storytel 1 Ay 69", "Gain 2 Ay Kod 80", "Exxen 3 Ay Reklamlı 130",
    "Hediye Kahve Coffy 80", "CapCut Pro Kişisel 1 Ay 150",
    "Canva Pro Sınırsızdır", "Semrush 140", "Kaspersky Pro 1 Yıl 170",
    
    # Active Peer Trader Signatures
    "Getirfinansa davet kodum", "On mobile davet kodum",
    "Yemeksepeti 500/250", "Yemeksepeti 400/200", "Yemeksepeti 375",
    "Tıkla Gelsin 400/200", "Trendyol Yemek 800/400", "ByNoGame 250",
    "Turna 600", "Turna 500", "Enuygun 500", "Biletinial Selfy",
    "Migros 500/150", "Migros Sanal Market", "Pepsi 2.5L 2 TL",
    "Kazandırio 500 TL", "frebayt 1 gb", "TOD Sezonluk Süper Lig",
    "TOD Taraftar Paketi", "S Sport Plus Yıllık", "BluTV 1 Yıl"
]

async def run_discovery():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    
    print(f"[*] {len(SEARCH_QUERIES)} Farklı Tüccar Sorgusu ile Telegram Taranıyor...\n")

    discovered_candidates = {}

    for q in SEARCH_QUERIES:
        try:
            res = await client(SearchGlobalRequest(
                q=q,
                filter=InputMessagesFilterEmpty(),
                min_date=None,
                max_date=None,
                offset_rate=0,
                offset_peer=InputPeerEmpty(),
                offset_id=0,
                limit=100
            ))
            chat_map = {c.id: c for c in res.chats}
            for m in res.messages:
                peer = m.peer_id
                cid = getattr(peer, 'channel_id', None) or getattr(peer, 'chat_id', None)
                chat = chat_map.get(cid)
                if not chat:
                    continue
                u = getattr(chat, 'username', None)
                if not u:
                    continue
                u_clean = u.lower().strip()
                
                # STRICT RULE: Must NOT be in the 1,470 excluded set
                if u_clean in EXCLUDED_SET:
                    continue

                is_mega = getattr(chat, 'megagroup', False)
                is_broad = getattr(chat, 'broadcast', False)
                
                # Must be supergroup, NOT a broadcast channel
                if not is_mega or is_broad:
                    continue

                title = getattr(chat, 'title', '')
                msg_txt = m.message or ""

                if u_clean not in discovered_candidates:
                    discovered_candidates[u_clean] = {
                        "username": u_clean,
                        "title": title,
                        "matched_queries": set(),
                        "live_messages": []
                    }

                discovered_candidates[u_clean]["matched_queries"].add(q)
                if msg_txt and len(discovered_candidates[u_clean]["live_messages"]) < 3:
                    clean_msg = " ".join(msg_txt.split())
                    if len(clean_msg) > 130:
                        clean_msg = clean_msg[:130] + "..."
                    if clean_msg not in discovered_candidates[u_clean]["live_messages"]:
                        discovered_candidates[u_clean]["live_messages"].append({
                            "date": str(m.date),
                            "sender_id": m.sender_id,
                            "text": clean_msg
                        })

            print(f"Sorgu: '{q:<32}' -> Bulunan Yeni Grup Sayısı: {len(discovered_candidates)}")
            await asyncio.sleep(0.8)
        except Exception as e:
            print(f"Sorgu hatası '{q}': {e}")

    print(f"\n=======================================================")
    print(f"🎉 TOPLAM MEVCUT/KARA LİSTEDE OLMAYAN TÜCCAR GRUBU: {len(discovered_candidates)}")
    print(f"=======================================================\n")

    result_list = []
    for u, d in discovered_candidates.items():
        d["matched_queries"] = list(d["matched_queries"])
        result_list.append(d)
        print(f"[YENİ GRUP ✅] @{u:<25} | {d['title'][:28]:<28} | Eşleşen: {d['matched_queries']}")

    with open("kesinlikle_yeni_tuccar_gruplari.json", "w", encoding="utf-8") as f:
        json.dump(result_list, f, ensure_ascii=False, indent=2)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(run_discovery())
