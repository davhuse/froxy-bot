import asyncio
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
import urllib.request
import urllib.parse
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession
from telethon.errors import (
    FloodWaitError, UsernameInvalidError, UsernameNotOccupiedError,
    ChannelPrivateError, ChatAdminRequiredError
)

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

SESSION_FILE = "session_7384.txt"
if not os.path.exists(SESSION_FILE):
    SESSION_FILE = "froxy_session_output.txt"

with open(SESSION_FILE, "r", encoding="utf-8") as f:
    SESSION_STRING = f.read().strip()

# -------------------------------------------------------------
# 1. COMPILE 100% EXHAUSTIVE MASTER BLACKLIST / KNOWN LIST
# -------------------------------------------------------------
def compile_master_known():
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

    print(f"[*] Toplam Bilinen / Kara Listedeki Grup Sayısı: {len(known)}")
    return known

# -------------------------------------------------------------
# 2. SEARCH KEYWORDS & FILTER PATTERNS
# -------------------------------------------------------------
SEARCH_KEYWORDS = [
    # Kupon, Çek, Kod
    "kupon satış", "kupon alım satım", "kupon satis", "kupon pazar", "kupon borsa",
    "çek satış", "cek satis", "çek alım satım", "cek alim satim", "çek pazarı",
    "kod satış", "kod alım satım", "indirim kodu satış", "indirim kupon",
    "yemeksepeti kupon", "trendyol yemek", "getir indirim", "migros indirim",
    "kupon takas", "kupon ilan", "kod pazarı", "kupon paylasim",
    
    # Hesap & Dijital Satış
    "hesap satış", "hesap alım satım", "hesap alim satim", "hesap pazarı",
    "dijital hesap", "premium hesap satış", "chatgpt hesap", "chatgpt plus",
    "canva pro", "canva lisans", "netflix hesap", "netflix 4k", "spotify premium",
    "youtube premium", "adobe creative cloud", "gemini pro", "claude pro",
    "vpn hesap", "gmail alım satım", "sosyal medya hesap",
    
    # Lisans & Key
    "lisans satış", "lisans alım satım", "key satış", "windows lisans",
    "office 365 lisans", "antivirüs lisans", "yazılım alım satım", "script satış",
    "dijital ürün satış", "dijital tedarik", "sanal ticaret",
    
    # Pazar & Ticaret & SMM
    "smm pazar", "smm bayi", "smm ticaret", "takipçi satış", "sosyal medya pazarı",
    "dijital pazar yeri", "dijital pazar", "freelance pazar", "webmaster ticaret",
    "ticaret grubu", "al sat pazar", "ilan alım satım", "shopier satış", "r10 ticaret"
]

BETTING_TERMS = [
    "bahis", "casino", "slot", "sweet bonanza", "gates of olympus", "rulet",
    "blackjack", "iddaa", "tipster", "kupon tahmin", "maç tahmin", "oran şikesi",
    "bet", "deneme bonusu", "bonus veren", "pragmatic", "güvenilir bahis",
    "canlı bahis", "roll", "aviator", "zeplin"
]

SPAM_ILLEGAL_TERMS = [
    "cc mail", "carding", "warez", "crack", "nulled", "escort", "porno", "lezbiyen",
    "gay", "ifsa", "ifşa", "tr ifsa", "yetiskin", "18+", "+18", "vip grup", "link tl"
]

GAME_ACCOUNT_TERMS = [
    "brawl stars", "brawlstars", "clash royale", "clash of clans", "pes mobile",
    "efootball", "free fire", "wolfteam", "growtopia", "standoff", "supercell",
    "mobile legends", "mlbb", "metin2", "zula hesap"
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
    "fiyat", "tl", "₺", "stok", "dm", "özelden", "teslim", "güvenli", "aracı", "ilan", "devir"
]

# -------------------------------------------------------------
# 3. WEB SEARCH & SCRAPING CANDIDATES
# -------------------------------------------------------------
def search_web_candidates():
    found_users = set()
    queries = [
        'site:t.me "kupon satış" telegram',
        'site:t.me "hesap alım satım" telegram',
        'site:t.me "lisans satış" telegram',
        'site:t.me "dijital pazar" telegram',
        'site:t.me "kupon çek kod" telegram',
        'site:t.me "smm pazar" telegram',
        'site:t.me "ticaret grubu" telegram'
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for q in queries:
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(q)}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                for m in re.finditer(r"(?:t\.me/|telegram\.me/)([a-zA-Z0-9_]{4,32})", html):
                    u = m.group(1).lower()
                    if u not in {"joinchat", "share", "addstickers", "proxy", "html", "bot"}:
                        found_users.add(u)
        except Exception:
            pass
            
    print(f"[*] Web Dizinlerinden Bulunan Aday Sayısı: {len(found_users)}")
    return found_users

# -------------------------------------------------------------
# 4. MAIN TELEGRAM DISCOVERY & INSPECTION ENGINE
# -------------------------------------------------------------
async def run_discovery_and_verification():
    master_known = compile_master_known()
    
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("[!] Hata: Telegram oturumu yetkilendirilemedi!")
        return

    me = await client.get_me()
    print(f"[+] Giriş Başarılı: {me.first_name} (@{me.username or 'yok'}) | ID: {me.id}")

    candidates = set()

    # Step A: Web search candidates
    web_candidates = search_web_candidates()
    for u in web_candidates:
        if u not in master_known:
            candidates.add(u)

    # Step B: Telegram Global Search
    print(f"[*] Telegram Global Arama Başlatılıyor ({len(SEARCH_KEYWORDS)} sorgu)...")
    for idx, kw in enumerate(SEARCH_KEYWORDS):
        try:
            res = await client(SearchRequest(q=kw, limit=50))
            for chat in getattr(res, 'chats', []):
                u = getattr(chat, 'username', None)
                if u:
                    u_clean = u.strip().lower()
                    if u_clean not in master_known:
                        candidates.add(u_clean)
            await asyncio.sleep(1.0)
        except FloodWaitError as e:
            print(f"[!] FloodWait: {e.seconds}s bekleniyor...")
            await asyncio.sleep(e.seconds + 1)
        except Exception:
            pass

    print(f"[*] Toplam Taranacak Benzersiz Aday Sayısı: {len(candidates)}")

    # Step C: Deep Live Message & Activity Inspection
    print(f"[*] Canlı Mesaj ve Grup Uygunluk Denetimi Başlatılıyor...")
    
    now = datetime.now(timezone.utc)
    verified_groups = []
    
    cand_list = sorted(list(candidates))
    checked_count = 0
    
    while cand_list:
        uname = cand_list.pop(0)
        checked_count += 1
        
        try:
            entity = await client.get_entity(uname)
            
            # Check 1: Must be a Supergroup / Megagroup, NOT a broadcast channel
            is_broad = getattr(entity, 'broadcast', False)
            is_mega = getattr(entity, 'megagroup', False) or getattr(entity, 'gigagroup', False)
            if is_broad or not is_mega:
                continue

            # Check 2: Get Full Chat Information
            try:
                full = await client(GetFullChannelRequest(entity))
                full_chat = full.full_chat
            except Exception:
                continue

            title = getattr(entity, 'title', '') or ''
            about = getattr(full_chat, 'about', '') or ''
            members = getattr(full_chat, 'participants_count', 0) or 0
            
            # Check 3: Member count filter (must have at least 70 members)
            if members < 70:
                continue

            combined_meta = f"{title}\n{about}".lower()

            # Check 4: Betting / Gambling / Illegal Filter in Meta
            if any(bt in combined_meta for bt in BETTING_TERMS):
                continue
            if any(st in combined_meta for st in SPAM_ILLEGAL_TERMS):
                continue
            if any(gt in combined_meta for gt in GAME_ACCOUNT_TERMS):
                continue
            if any(ad in combined_meta for ad in ADMIN_DEAL_TERMS):
                continue

            # Check 5: Member message permissions (Cannot be read-only for members)
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                continue

            # Check 6: Pull live messages (Last 40 messages)
            messages = await client.get_messages(entity, limit=40)
            if not messages or len(messages) < 5:
                continue

            # Check 7: Freshness / Not Dead
            latest = messages[0]
            if not latest or not latest.date:
                continue
            msg_d = latest.date
            if msg_d.tzinfo is None:
                msg_d = msg_d.replace(tzinfo=timezone.utc)
            age_hours = (now - msg_d).total_seconds() / 3600.0
            
            # Must have sent a message within last 48 hours
            if age_hours > 48.0:
                continue

            # Check 8: Sender Diversity (Anti-Single Admin / Anti-Bot Broadcast)
            sample_msgs = messages[:30]
            senders = [m.sender_id for m in sample_msgs if m and m.sender_id]
            unique_senders = len(set(senders))
            
            if len(sample_msgs) >= 15 and unique_senders < 5:
                continue
            if len(sample_msgs) < 15 and unique_senders < 3:
                continue

            # Check 9: Analyze live message contents for Relevance vs Betting/Admin Deals
            msg_texts = [m.text.lower() for m in messages if m and m.text]
            all_text_blob = " \n ".join(msg_texts)

            # Check betting in chat
            if any(bt in all_text_blob for bt in BETTING_TERMS):
                continue
            if any(st in all_text_blob for st in SPAM_ILLEGAL_TERMS):
                continue

            # Score positive relevance
            pos_matches = []
            for pt in POSITIVE_TERMS:
                cnt = all_text_blob.count(pt)
                if cnt > 0:
                    pos_matches.append((pt, cnt))

            total_pos_score = sum(cnt for _, cnt in pos_matches)
            
            # If there is almost no commerce/target keyword across 40 messages, skip
            if total_pos_score < 3:
                continue

            # Extract sample snippets
            sample_snippets = []
            for m in messages:
                if m and m.text and len(m.text) > 10:
                    clean_txt = " ".join(m.text.split())
                    if len(clean_txt) > 120:
                        clean_txt = clean_txt[:120] + "..."
                    sample_snippets.append(clean_txt)
                    if len(sample_snippets) >= 3:
                        break

            # Categorize
            category = "Dijital Ticaret & Pazar"
            if any(k in combined_meta or k in all_text_blob for k in ["kupon", "çek", "cek", "yemeksepeti", "trendyol"]):
                category = "Kupon & Çek & Kod Pazarı"
            elif any(k in combined_meta or k in all_text_blob for k in ["lisans", "windows", "office", "antivirüs"]):
                category = "Lisans & Key & Yazılım"
            elif any(k in combined_meta or k in all_text_blob for k in ["chatgpt", "canva", "netflix", "spotify", "hesap"]):
                category = "Premium Hesap & Dijital Ürün"
            elif any(k in combined_meta or k in all_text_blob for k in ["smm", "takipçi", "sosyal medya"]):
                category = "SMM & Sosyal Medya Hizmetleri"

            group_data = {
                "username": uname,
                "title": title,
                "members": members,
                "category": category,
                "last_message_hours_ago": round(age_hours, 1),
                "unique_senders_last_30": unique_senders,
                "total_messages_inspected": len(messages),
                "relevance_score": total_pos_score,
                "matched_keywords": [p[0] for p in pos_matches[:8]],
                "sample_messages": sample_snippets,
                "t_me_link": f"https://t.me/{uname}"
            }
            
            verified_groups.append(group_data)
            print(f"[ONAYLANDI ✅ #{len(verified_groups)}] @{uname} | {title[:28]} | Üye: {members} | Son Mesaj: {round(age_hours,1)}s | Gönderici: {unique_senders} | Kat: {category}")
            
            # Step D: Also extract sibling group mentions inside this verified group to discover more!
            for m in messages:
                if m and m.text:
                    for found in re.finditer(r"(?:t\.me/|@)([A-Za-z0-9_]{4,32})", m.text):
                        sibling = found.group(1).lower()
                        if sibling not in master_known and sibling not in cand_list and sibling not in {"joinchat", "share", "bot"}:
                            cand_list.append(sibling)

            await asyncio.sleep(0.4)

        except FloodWaitError as e:
            print(f"[!] FloodWait: {e.seconds}s bekleniyor...")
            await asyncio.sleep(e.seconds + 2)
        except (UsernameInvalidError, UsernameNotOccupiedError, ChannelPrivateError):
            pass
        except Exception:
            pass

    # Sort verified groups by freshness and relevance
    verified_groups.sort(key=lambda x: (x["last_message_hours_ago"], -x["relevance_score"], -x["members"]))

    print(f"\n=======================================================")
    print(f"🎉 TARAMA TAMAMLANDI: Toplam {len(verified_groups)} Yeni & Birebir Hedefe Uygun Grup Doğrulandı!")
    print(f"=======================================================\n")

    # Save to JSON
    with open("yeni_birebir_hedef_gruplar.json", "w", encoding="utf-8") as f:
        json.dump(verified_groups, f, ensure_ascii=False, indent=2)

    # Save to TXT
    with open("yeni_birebir_hedef_gruplar.txt", "w", encoding="utf-8") as f:
        for g in verified_groups:
            f.write(f"{g['username']}\n")

    print("[*] Sonuçlar 'yeni_birebir_hedef_gruplar.json' ve 'yeni_birebir_hedef_gruplar.txt' dosyalarına kaydedildi.")

if __name__ == "__main__":
    asyncio.run(run_discovery_and_verification())
