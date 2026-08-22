import asyncio
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import InputPeerEmpty, InputMessagesFilterEmpty
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

SESSION_FILE = "froxy_session_output.txt"
with open(SESSION_FILE, "r", encoding="utf-8") as f:
    SESSION_STRING = f.read().strip()

# -------------------------------------------------------------
# 1. COMPILE COMPLETE MASTER BLACKLIST / KNOWN SET
# -------------------------------------------------------------
def compile_master_blacklist():
    known = set()
    for fname in os.listdir("."):
        if not (fname.endswith(".json") or fname.endswith(".txt")):
            continue
        if fname in ["yeni_birebir_hedef_gruplar.json", "yeni_birebir_hedef_gruplar.txt"]:
            continue
            
        fpath = os.path.join(".", fname)
        try:
            if fname.endswith(".json"):
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, str):
                                u = item.strip().lower().lstrip("@")
                                if 3 < len(u) < 35:
                                    known.add(u)
                            elif isinstance(item, dict):
                                for k in ["username", "group", "id", "chat_id", "link"]:
                                    v = item.get(k)
                                    if v and isinstance(v, str):
                                        u = v.strip().lower().lstrip("@").replace("https://t.me/", "")
                                        if 3 < len(u) < 35:
                                            known.add(u)
                    elif isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(k, str) and 3 < len(k) < 35:
                                known.add(k.strip().lower().lstrip("@"))
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict):
                                        for subk in ["username", "group", "link"]:
                                            subv = item.get(subk)
                                            if subv and isinstance(subv, str):
                                                u = subv.strip().lower().lstrip("@").replace("https://t.me/", "")
                                                if 3 < len(u) < 35:
                                                    known.add(u)
                                    elif isinstance(item, str):
                                        u = item.strip().lower().lstrip("@")
                                        if 3 < len(u) < 35:
                                            known.add(u)
            elif fname.endswith(".txt"):
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        for m in re.finditer(r"(?:t\.me/|@|^|\s)([a-zA-Z0-9_]{4,32})", line):
                            u = m.group(1).lower()
                            if u not in {"joinchat", "share", "proxy", "http", "https", "true", "false", "none"}:
                                known.add(u)
        except Exception:
            pass

    print(f"[*] Toplam Bilinen / Kara Listedeki Grup Sayısı: {len(known)}", flush=True)
    return known

# -------------------------------------------------------------
# 2. SEARCH QUERIES (HIGH-PRECISION COMMERCE / TARGET)
# -------------------------------------------------------------
GLOBAL_SEARCH_QUERIES = [
    # Kupon, Çek, İndirim Kodu
    "yemeksepeti kupon satılık", "yemeksepeti kupon alınır", "yemeksepeti kod satılık",
    "trendyol yemek kupon satılık", "trendyol kupon satılık", "trendyol indirim kodu",
    "getir yemek kupon", "getir kupon satılık", "migros hediye çeki satılık", "migros çek satılık",
    "migros money kod", "kupon çek kod satılık", "kupon satılık dm", "kod satılık dm",
    "çek satılık dm", "kupon alınır dm", "kod alınır dm", "çek alınır dm",
    "turna çek satılık", "enuygun çek satılık", "hediye çeki satılık", "alışveriş çeki satılık",
    "kupon borsa alım satım", "kupon takas satılık", "indirim çeki alım satım",
    
    # Dijital Hesap & Abonelik Satışı
    "chatgpt plus hesap satılık", "chatgpt hesap satılık", "chatgpt plus devir",
    "canva pro davet satılık", "canva pro ömür boyu", "canva lisans satılık",
    "netflix 4k ultra hesap", "netflix hesap satılık", "spotify premium davet",
    "youtube premium aile davet", "adobe creative cloud lisans", "adobe cc satılık",
    "gemini advanced hesap", "claude pro hesap satılık", "perplexity pro satılık",
    "nordvpn hesap satılık", "vpn hesap satılık", "gmail hesap satılık",
    "eski tarihli gmail", "sosyal medya hesap alım satım", "instagram hesap satılık",
    "tiktok hesap satılık", "telegram hesap satılık",
    
    # Lisans & Key & Yazılım
    "windows 11 pro lisans key", "windows 10 pro key satılık", "office 365 lisans key",
    "microsoft 365 hesap satılık", "kaspersky premium key", "antivirüs key satılık",
    "bot script satılık", "yazılım satış pazar", "dijital ürün alım satım",
    "sanal ticaret alım satım", "dijital tedarikçi pazar",
    
    # Pazar, SMM & Ticaret
    "smm pazar alım satım", "smm bayi takipçi", "sosyal medya takipçi satılık",
    "dijital pazar yeri al sat", "ticaret grubu alım satım", "al sat ticaret grubu",
    "shopier ilan alım satım", "freelance iş alım satım", "webmaster ticaret pazar"
]

# -------------------------------------------------------------
# 3. STRICT FILTERS
# -------------------------------------------------------------
BETTING_TERMS = [
    "bahis", "casino", "slot", "sweet bonanza", "gates of olympus", "rulet",
    "blackjack", "iddaa", "tipster", "kupon tahmin", "maç tahmin", "oran şikesi",
    "bet", "deneme bonusu", "bonus veren", "pragmatic", "güvenilir bahis",
    "canlı bahis", "roll", "aviator", "zeplin", "canlibahis", "kripto sinyal"
]

SPAM_ILLEGAL_TERMS = [
    "cc mail", "carding", "warez", "crack", "nulled", "escort", "porno", "lezbiyen",
    "gay", "ifsa", "ifşa", "tr ifsa", "yetiskin", "18+", "+18", "vip grup", "link tl",
    "illegal", "paneli patlat", "datacı", "muris", "gsm tc", "cc alım"
]

GAME_ACCOUNT_TERMS = [
    "brawl stars", "brawlstars", "clash royale", "clash of clans", "pes mobile",
    "efootball", "free fire", "wolfteam", "growtopia", "standoff", "supercell",
    "mobile legends", "mlbb"
]

ADMIN_DEAL_TERMS = [
    "sıcak fırsatlar", "sicak firsatlar", "fırsat avcısı", "firsat avcisi",
    "amazon fırsat", "affiliate", "sadece admin paylaşır", "yalnızca admin",
    "mesaj yazmak yasaktır", "sohbete kapalı", "paylaşım kanalı", "duyuru kanalı",
    "indirim haberleri", "günün fırsatları"
]

POSITIVE_TERMS = [
    "kupon", "çek", "cek", "kod", "indirim", "yemeksepeti", "trendyol", "getir", "migros",
    "hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "gemini", "claude",
    "lisans", "key", "windows", "office", "antivirüs", "vpn", "smm", "panel",
    "takipçi", "sosyal medya", "dijital", "ticaret", "alım", "satım", "satış", "satis",
    "fiyat", "tl", "₺", "stok", "dm", "özelden", "teslim", "güvenli", "aracı", "ilan", "devir",
    "pazar", "market", "al sat", "tedarik", "shopier", "hizmet"
]

async def run_master_finder():
    master_known = compile_master_blacklist()
    
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("[!] Hata: Oturum açılamadı!", flush=True)
        return

    me = await client.get_me()
    print(f"[+] Oturum Açıldı: {me.first_name} (@{me.username or 'yok'}) | ID: {me.id}\n", flush=True)

    # Dictionary to hold candidate groups with their live messages
    # uname -> {"entity": entity, "messages": [msg_objs], "matched_queries": set()}
    group_candidates = {}

    print(f"[*] {len(GLOBAL_SEARCH_QUERIES)} Hedef Sorgu ile Telegram Canlı Mesaj Taraması Başlatılıyor...\n", flush=True)

    now = datetime.now(timezone.utc)

    for idx, q in enumerate(GLOBAL_SEARCH_QUERIES, 1):
        try:
            res = await client(SearchGlobalRequest(
                q=q,
                filter=InputMessagesFilterEmpty(),
                min_date=None,
                max_date=None,
                offset_rate=0,
                offset_peer=InputPeerEmpty(),
                offset_id=0,
                limit=35
            ))
            
            chat_map = {c.id: c for c in res.chats}
            new_found = 0
            
            for msg in res.messages:
                peer = msg.peer_id
                cid = getattr(peer, 'channel_id', None) or getattr(peer, 'chat_id', None)
                if not cid:
                    continue
                chat = chat_map.get(cid)
                if not chat:
                    continue
                username = getattr(chat, 'username', None)
                if not username:
                    continue
                    
                u_clean = username.strip().lower()
                
                # Check against blacklist
                if u_clean in master_known:
                    continue
                    
                # Must be supergroup/megagroup (NOT channel broadcast)
                is_mega = getattr(chat, 'megagroup', False) or getattr(chat, 'gigagroup', False)
                is_broad = getattr(chat, 'broadcast', False)
                if is_broad or not is_mega:
                    continue
                    
                title = getattr(chat, 'title', '') or ''
                title_lower = title.lower()
                
                # Filter out betting/illegal from title immediately
                if any(bt in title_lower for bt in BETTING_TERMS):
                    continue
                if any(st in title_lower for st in SPAM_ILLEGAL_TERMS):
                    continue
                if any(gt in title_lower for gt in GAME_ACCOUNT_TERMS):
                    continue
                if any(ad in title_lower for ad in ADMIN_DEAL_TERMS):
                    continue

                if u_clean not in group_candidates:
                    group_candidates[u_clean] = {
                        "username": u_clean,
                        "title": title,
                        "entity": chat,
                        "messages": [],
                        "senders": set(),
                        "matched_queries": set()
                    }
                    new_found += 1

                if msg.message:
                    group_candidates[u_clean]["messages"].append({
                        "date": msg.date,
                        "sender_id": msg.sender_id,
                        "text": msg.message
                    })
                    if msg.sender_id:
                        group_candidates[u_clean]["senders"].add(msg.sender_id)
                group_candidates[u_clean]["matched_queries"].add(q)

            print(f"[{idx}/{len(GLOBAL_SEARCH_QUERIES)}] Sorgu: '{q}' -> Bulunan Yeni Hedef Grup: {new_found} (Toplam Aday Havuzu: {len(group_candidates)})", flush=True)
            await asyncio.sleep(1.2)

        except FloodWaitError as e:
            print(f"[!] FloodWait: {e.seconds}s bekleniyor...", flush=True)
            await asyncio.sleep(e.seconds + 2)
        except Exception as e:
            print(f"Sorgu hatası '{q}': {e}", flush=True)

    print(f"\n=======================================================", flush=True)
    print(f"[*] ARAMA TAMAMLANDI! Toplam {len(group_candidates)} Yeni Aday Grup Toplandı.", flush=True)
    print(f"[*] Canlı Sohbet ve Mesaj Kalitesi Denetimine Geçiliyor...", flush=True)
    print(f"=======================================================\n", flush=True)

    vetted_groups = []

    for uname, data in group_candidates.items():
        title = data["title"]
        msgs = data["messages"]
        senders = data["senders"]
        
        # 1. Freshness / Not dead
        if not msgs:
            continue
            
        latest_date = max(m["date"] for m in msgs)
        if latest_date.tzinfo is None:
            latest_date = latest_date.replace(tzinfo=timezone.utc)
            
        age_hours = (now - latest_date).total_seconds() / 3600.0
        
        # 2. Content analysis across all captured live messages
        all_text = " \n ".join(m["text"].lower() for m in msgs)
        
        # Negative filter in message content
        if any(bt in all_text for bt in BETTING_TERMS):
            continue
        if any(st in all_text for st in SPAM_ILLEGAL_TERMS):
            continue

        # Score positive target relevance
        pos_matches = []
        for pt in POSITIVE_TERMS:
            cnt = all_text.count(pt)
            if cnt > 0:
                pos_matches.append((pt, cnt))

        relevance_score = sum(cnt for _, cnt in pos_matches)
        if relevance_score < 2:
            continue

        # Clean sample message snippets
        samples = []
        for m in msgs:
            txt = m["text"].strip()
            if len(txt) > 10:
                clean_txt = " ".join(txt.split())
                if len(clean_txt) > 120:
                    clean_txt = clean_txt[:120] + "..."
                if clean_txt not in samples:
                    samples.append(clean_txt)
                if len(samples) >= 3:
                    break

        # Categorize
        category = "Dijital Ticaret & Pazar"
        combined_text = f"{title}\n{all_text}".lower()
        if any(k in combined_text for k in ["kupon", "çek", "cek", "yemeksepeti", "trendyol", "getir", "migros"]):
            category = "Kupon & Çek & Kod Pazarı"
        elif any(k in combined_text for k in ["lisans", "windows", "office", "antivirüs", "key", "kaspersky"]):
            category = "Lisans & Key & Yazılım"
        elif any(k in combined_text for k in ["chatgpt", "canva", "netflix", "spotify", "hesap", "gmail"]):
            category = "Premium Hesap & Dijital Ürün"
        elif any(k in combined_text for k in ["smm", "takipçi", "sosyal medya"]):
            category = "SMM & Sosyal Medya Hizmetleri"

        group_item = {
            "username": uname,
            "title": title,
            "category": category,
            "latest_message_date": latest_date.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "last_message_hours_ago": round(age_hours, 1),
            "unique_senders_seen": len(senders),
            "captured_live_messages": len(msgs),
            "relevance_score": relevance_score,
            "matched_queries": list(data["matched_queries"]),
            "matched_keywords": [p[0] for p in pos_matches[:8]],
            "sample_messages": samples,
            "t_me_link": f"https://t.me/{uname}"
        }

        vetted_groups.append(group_item)
        print(f"[ONAYLANDI ✅ #{len(vetted_groups)}] @{uname} | {title[:28]} | Son Mesaj: {round(age_hours,1)}s önce | Gönderici: {len(senders)} | Kat: {category}", flush=True)

    # Sort vetted groups by freshness and relevance
    vetted_groups.sort(key=lambda x: (x["last_message_hours_ago"], -x["relevance_score"]))

    print(f"\n=======================================================", flush=True)
    print(f"🎉 DOĞRULAMA TAMAMLANDI: Toplam {len(vetted_groups)} Adet 1'e 1 Hedefe Uygun & Onaylı Grup Çıkarıldı!", flush=True)
    print(f"=======================================================\n", flush=True)

    # Save to JSON
    with open("yeni_birebir_hedef_gruplar.json", "w", encoding="utf-8") as f:
        json.dump(vetted_groups, f, ensure_ascii=False, indent=2)

    # Save to TXT
    with open("yeni_birebir_hedef_gruplar.txt", "w", encoding="utf-8") as f:
        for g in vetted_groups:
            f.write(f"{g['username']}\n")

    print("[*] Dosyalar kaydedildi: 'yeni_birebir_hedef_gruplar.json' ve 'yeni_birebir_hedef_gruplar.txt'", flush=True)

if __name__ == "__main__":
    asyncio.run(run_master_finder())
