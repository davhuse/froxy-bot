import asyncio
import json
import os
import re
import sys
from telethon import TelegramClient
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import InputPeerEmpty, InputMessagesFilterEmpty
from telethon.sessions import StringSession
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

SESSION_FILE = "froxy_session_output.txt"
with open(SESSION_FILE, "r", encoding="utf-8") as f:
    SESSION_STRING = f.read().strip()

# 1. Load EXHAUSTIVE exclusion set (1,470 entries)
with open("exhaustive_excluded_groups.json", "r", encoding="utf-8") as f:
    EXCLUDED_SET = set(json.load(f))

print(f"[*] Toplam Kesin Yasaklı / Mevcut Grup Sayısı: {len(EXCLUDED_SET)}")

# 2. Broad and diverse Turkish digital commerce search queries
BROAD_SEARCH_QUERIES = [
    # Food / Coupon / Code / Voucher
    "yemeksepeti kupon", "trendyol indirim kodu", "getir indirim", "tıkla gelsin kupon",
    "migros hediye çeki", "enuygun indirim", "turna bilet kodu", "pepsi kapak kodu",
    "kazandırio kod", "bedava internet kod", "biletinial kod", "sinema bilet kodu",
    "carrefour çek", "a101 hediye çeki", "şok market kupon",
    
    # Digital Accounts / Subscriptions / Licenses
    "chatgpt plus satılık", "gemini pro hesap", "canva pro lisans", "netflix hesap satılık",
    "spotify premium hesap", "duolingo plus", "adobe creative cloud key", "windows 11 pro lisans",
    "office 365 lisans key", "kaspersky lisans", "autocad lisans", "semrush hesap",
    "tod tv hesap", "exxen hesap satılık", "blutv hesap", "s sport hesap",
    
    # P2P Trading / Marketplace / SMM / Freelance
    "dijital ürün alım satım", "hesap alım satım ticaret", "kupon kod takas",
    "sosyal medya hesap alım", "instagram hesap satılık", "tiktok hesap satılık",
    "youtube kanal satılık", "smm panel bakiye", "takipçi satış grubu",
    "iban kiralama kadın erkek", "reklam alım satım grubu", "e-ticaret yardımlaşma",
    "dropshipping türkiye", "amazon satıcı grubu", "trendyol satıcı grubu"
]

BETTING_TERMS = [
    "bahis", "casino", "slot", "sweet bonanza", "gates of olympus", "rulet",
    "blackjack", "iddaa", "tipster", "kupon tahmin", "maç tahmin", "oran şikesi",
    "bet", "deneme bonusu", "bonus veren", "pragmatic", "güvenilir bahis"
]

SPAM_TERMS = [
    "cc mail", "carding", "warez", "crack", "nulled", "escort", "porno", "lezbiyen",
    "ifsa", "ifşa", "+18", "illegal", "paneli patlat", "datacı", "muris"
]

async def run_discovery():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    
    print(f"[*] {len(BROAD_SEARCH_QUERIES)} Farklı Dijital Ticaret Sorgusu Taranıyor...\n")

    discovered_groups = {}
    now = datetime.now(timezone.utc)

    for q in BROAD_SEARCH_QUERIES:
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
                title_lower = title.lower()

                # Filter betting / spam titles
                if any(bt in title_lower for bt in BETTING_TERMS):
                    continue
                if any(st in title_lower for st in SPAM_TERMS):
                    continue

                msg_txt = m.message or ""
                msg_lower = msg_txt.lower()

                if any(bt in msg_lower for bt in BETTING_TERMS):
                    continue
                if any(st in msg_lower for st in SPAM_TERMS):
                    continue

                if u_clean not in discovered_groups:
                    discovered_groups[u_clean] = {
                        "username": u_clean,
                        "title": title,
                        "matched_queries": set(),
                        "unique_senders": set(),
                        "sample_messages": []
                    }

                discovered_groups[u_clean]["matched_queries"].add(q)
                if m.sender_id:
                    discovered_groups[u_clean]["unique_senders"].add(m.sender_id)

                if msg_txt and len(discovered_groups[u_clean]["sample_messages"]) < 3:
                    clean_msg = " ".join(msg_txt.split())
                    if len(clean_msg) > 130:
                        clean_msg = clean_msg[:130] + "..."
                    if clean_msg not in discovered_groups[u_clean]["sample_messages"]:
                        discovered_groups[u_clean]["sample_messages"].append(clean_msg)

            print(f"Sorgu: '{q:<32}' -> Toplam Yeni Keşif: {len(discovered_groups)}")
            await asyncio.sleep(0.8)
        except Exception as e:
            print(f"Sorgu hatası '{q}': {e}")

    print(f"\n=======================================================")
    print(f"🎉 TOPLAM MEVCUT/KARA LİSTEDE KESİNLİKLE OLMAYAN YENİ GRUP: {len(discovered_groups)}")
    print(f"=======================================================\n")

    result_list = []
    for u, d in discovered_groups.items():
        # Keep groups with multiple real senders
        d["matched_queries"] = list(d["matched_queries"])
        d["unique_sender_count"] = len(d["unique_senders"])
        del d["unique_senders"]
        
        result_list.append(d)
        print(f"[YENİ GRUP ✅] @{u:<25} | {d['title'][:28]:<28} | Gönderici: {d['unique_sender_count']} | Eşleşen: {d['matched_queries']}")

    with open("kesinlikle_yepyeni_saf_gruplar.json", "w", encoding="utf-8") as f:
        json.dump(result_list, f, ensure_ascii=False, indent=2)

    with open("kesinlikle_yepyeni_saf_gruplar.txt", "w", encoding="utf-8") as f:
        for g in result_list:
            f.write(f"{g['username']}\n")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(run_discovery())
