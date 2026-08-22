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
from telethon.sessions import StringSession
from telethon.errors import (
    FloodWaitError, UsernameInvalidError, UsernameNotOccupiedError,
    ChannelPrivateError, ChannelInvalidError
)

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

SESSION_FILE = "froxy_session_output.txt"
with open(SESSION_FILE, "r", encoding="utf-8") as f:
    SESSION_STRING = f.read().strip()

# -------------------------------------------------------------
# 1. EXHAUSTIVE BLACKLIST / KNOWN DATABASE
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
# 2. SEED ACTIVE TRADE GROUPS
# -------------------------------------------------------------
SEED_ACTIVE_GROUPS = [
    "kuponsat", "kuponhesapsatis", "ceksat", "letgoilanlari", "kuponsatisgrup",
    "alimsatimmerkezii", "ticaretyapn", "kodkuponmarketi", "yucekuponsatis",
    "ceksatkupon", "wishx_2", "zeroticaret", "ticaretgruptr", "kuponkodceksatis",
    "kodpazari", "YemekSepetiKuponu", "KodKuponMerkezi", "kuponkodmerkez",
    "herkesibeklerimm", "kuponyaticaret", "cek_kupon_kod_ilan", "Minakuponkodsatis",
    "kinseimedyaticaret", "dijitalticaretgrubu", "aTicaret", "mailalimsatimticaret",
    "satiskodtakasi", "kuponkodalimsatimm", "kuponindirimpazari", "mukyemek",
    "kuponvekodsatisgrubu", "kodmalf", "indirimruzgari1", "kuponindirimkodalisveris",
    "uygunkod", "kodalimsatim", "kuponalsatgurup", "bedavainternetkodalimsatim",
    "bedavainternetkod", "kuponindirimlisatis", "kuponceking", "me7alimsatim"
]

# -------------------------------------------------------------
# 3. STRICT FILTERS & CATEGORIES
# -------------------------------------------------------------
BETTING_TERMS = [
    "bahis", "casino", "slot", "sweet bonanza", "gates of olympus", "rulet",
    "blackjack", "iddaa", "tipster", "kupon tahmin", "maç tahmin", "oran şikesi",
    "bet", "deneme bonusu", "bonus veren", "pragmatic", "güvenilir bahis",
    "canlı bahis", "roll", "aviator", "zeplin", "canlibahis"
]

SPAM_ILLEGAL_TERMS = [
    "cc mail", "carding", "warez", "crack", "nulled", "escort", "porno", "lezbiyen",
    "gay", "ifsa", "ifşa", "tr ifsa", "yetiskin", "18+", "+18", "vip grup", "link tl",
    "illegal", "paneli patlat", "datacı", "muris", "gsm tc"
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
    "fiyat", "tl", "₺", "stok", "dm", "özelden", "teslim", "güvenli", "aracı", "ilan", "devir"
]

def search_web_directories():
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
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                for m in re.finditer(r"(?:t\.me/|telegram\.me/)([a-zA-Z0-9_]{4,32})", html):
                    u = m.group(1).lower()
                    if u not in {"joinchat", "share", "addstickers", "proxy", "html", "bot", "telegram", "channel"}:
                        found_users.add(u)
        except Exception:
            pass
            
    return found_users

# -------------------------------------------------------------
# 4. MAIN HARVEST & LIVE VERIFICATION PIPELINE
# -------------------------------------------------------------
async def run_pipeline():
    master_known = compile_master_blacklist()
    
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("[!] HATA: Telegram oturumu yetkilendirilemedi!", flush=True)
        return

    me = await client.get_me()
    print(f"[+] Giriş Başarılı: {me.first_name} (@{me.username or 'yok'}) | ID: {me.id}", flush=True)

    candidates = set()

    # Step A: Harvest from Web
    web_cands = search_web_directories()
    for u in web_cands:
        if u not in master_known:
            candidates.add(u)
    print(f"[*] Web aramasından eklenen aday sayısı: {len(candidates)}", flush=True)

    # Step B: Harvest from Active Seed Trade Groups
    print(f"[*] Aktif Seed Ticaret Gruplarının son mesajlarından çapraz linkler taranıyor ({len(SEED_ACTIVE_GROUPS)} grup)...", flush=True)
    for s_idx, seed in enumerate(SEED_ACTIVE_GROUPS):
        try:
            entity = await client.get_entity(seed)
            msgs = await client.get_messages(entity, limit=250)
            for m in msgs:
                if m and m.text:
                    for found in re.finditer(r"(?:t\.me/|@)([A-Za-z0-9_]{4,32})", m.text):
                        u = found.group(1).lower()
                        if u not in master_known and u not in candidates and u not in {
                            "joinchat", "share", "proxy", "bot", "channel", "http", "https", "support",
                            "admin", "destek", "yardim", "iletisim", "reklam"
                        }:
                            candidates.add(u)
            if (s_idx + 1) % 10 == 0:
                print(f"  -> {s_idx + 1}/{len(SEED_ACTIVE_GROUPS)} seed grup tarandı. Toplam aday: {len(candidates)}", flush=True)
            await asyncio.sleep(0.3)
        except Exception:
            pass

    print(f"\n[*] Toplam Taranacak Benzersiz Yeni Aday Sayısı: {len(candidates)}", flush=True)
    print(f"[*] Canlı Mesaj ve Grup Uygunluk Denetimi Başlatılıyor...\n", flush=True)

    now = datetime.now(timezone.utc)
    verified_groups = []
    
    cand_queue = sorted(list(candidates))
    checked_count = 0
    
    while cand_queue:
        uname = cand_queue.pop(0)
        checked_count += 1
        
        try:
            entity = await client.get_entity(uname)
            
            # 1. Supergroup / Megagroup Check (No channels, no private broadcasts)
            is_broad = getattr(entity, 'broadcast', False)
            is_mega = getattr(entity, 'megagroup', False) or getattr(entity, 'gigagroup', False)
            if is_broad or not is_mega:
                continue

            title = getattr(entity, 'title', '') or ''
            
            # 2. Metadata Negative Filter (Title)
            title_lower = title.lower()
            if any(bt in title_lower for bt in BETTING_TERMS):
                continue
            if any(st in title_lower for st in SPAM_ILLEGAL_TERMS):
                continue
            if any(gt in title_lower for gt in GAME_ACCOUNT_TERMS):
                continue
            if any(ad in title_lower for ad in ADMIN_DEAL_TERMS):
                continue

            # 3. Pull Live Messages (Last 35 messages)
            messages = await client.get_messages(entity, limit=35)
            if not messages or len(messages) < 5:
                continue

            # 4. Freshness / Not Dead Check
            latest = messages[0]
            if not latest or not latest.date:
                continue
            msg_d = latest.date
            if msg_d.tzinfo is None:
                msg_d = msg_d.replace(tzinfo=timezone.utc)
            age_hours = (now - msg_d).total_seconds() / 3600.0
            
            # Must be active within last 48 hours
            if age_hours > 48.0:
                continue

            # 5. Unique Sender Diversity Check (Anti-Single Admin / Anti-Bot Broadcast)
            sample_msgs = messages[:30]
            senders = [m.sender_id for m in sample_msgs if m and m.sender_id]
            unique_senders = len(set(senders))
            
            if len(sample_msgs) >= 15 and unique_senders < 5:
                continue
            if len(sample_msgs) < 15 and unique_senders < 3:
                continue

            # 6. Analyze Live Chat Content
            msg_texts = [m.text.lower() for m in messages if m and m.text]
            all_text_blob = " \n ".join(msg_texts)

            if any(bt in all_text_blob for bt in BETTING_TERMS):
                continue
            if any(st in all_text_blob for st in SPAM_ILLEGAL_TERMS):
                continue

            # 7. Positive Target Relevance Score
            pos_matches = []
            for pt in POSITIVE_TERMS:
                cnt = all_text_blob.count(pt)
                if cnt > 0:
                    pos_matches.append((pt, cnt))

            total_pos_score = sum(cnt for _, cnt in pos_matches)
            if total_pos_score < 3:
                continue

            # 8. Clean sample messages
            sample_snippets = []
            for m in messages:
                if m and m.text and len(m.text) > 10:
                    clean_txt = " ".join(m.text.split())
                    if len(clean_txt) > 120:
                        clean_txt = clean_txt[:120] + "..."
                    sample_snippets.append(clean_txt)
                    if len(sample_snippets) >= 3:
                        break

            # 9. Determine Category
            category = "Dijital Ticaret & Pazar"
            if any(k in title_lower or k in all_text_blob for k in ["kupon", "çek", "cek", "yemeksepeti", "trendyol", "getir", "migros"]):
                category = "Kupon & Çek & Kod Pazarı"
            elif any(k in title_lower or k in all_text_blob for k in ["lisans", "windows", "office", "antivirüs", "key"]):
                category = "Lisans & Key & Yazılım"
            elif any(k in title_lower or k in all_text_blob for k in ["chatgpt", "canva", "netflix", "spotify", "hesap", "gmail"]):
                category = "Premium Hesap & Dijital Ürün"
            elif any(k in title_lower or k in all_text_blob for k in ["smm", "takipçi", "sosyal medya"]):
                category = "SMM & Sosyal Medya Hizmetleri"

            # Approximate members or participants
            participants = getattr(entity, 'participants_count', None)

            group_data = {
                "username": uname,
                "title": title,
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
            print(f"[ONAYLANDI ✅ #{len(verified_groups)}] @{uname} | {title[:28]} | Son Mesaj: {round(age_hours,1)}s önce | Tekil Gönderici: {unique_senders} | Kat: {category}", flush=True)
            
            # Step 10: Dynamic sibling discovery from verified group messages
            for m in messages:
                if m and m.text:
                    for found in re.finditer(r"(?:t\.me/|@)([A-Za-z0-9_]{4,32})", m.text):
                        sibling = found.group(1).lower()
                        if sibling not in master_known and sibling not in cand_queue and sibling not in {"joinchat", "share", "proxy", "bot", "support", "destek"}:
                            cand_queue.append(sibling)

            await asyncio.sleep(0.3)

        except FloodWaitError as e:
            print(f"[!] FloodWait: {e.seconds}s bekleniyor...", flush=True)
            await asyncio.sleep(e.seconds + 2)
        except (UsernameInvalidError, UsernameNotOccupiedError, ChannelPrivateError, ChannelInvalidError):
            pass
        except Exception as e:
            pass

    # Sort verified groups by freshness and relevance score
    verified_groups.sort(key=lambda x: (x["last_message_hours_ago"], -x["relevance_score"]))

    print(f"\n=======================================================", flush=True)
    print(f"🎉 TARAMA TAMAMLANDI: Toplam {len(verified_groups)} Yeni & Birebir Hedefe Uygun Grup Doğrulandı!", flush=True)
    print(f"=======================================================\n", flush=True)

    with open("yeni_birebir_hedef_gruplar.json", "w", encoding="utf-8") as f:
        json.dump(verified_groups, f, ensure_ascii=False, indent=2)

    with open("yeni_birebir_hedef_gruplar.txt", "w", encoding="utf-8") as f:
        for g in verified_groups:
            f.write(f"{g['username']}\n")

    print("[*] Sonuçlar 'yeni_birebir_hedef_gruplar.json' ve 'yeni_birebir_hedef_gruplar.txt' dosyalarına kaydedildi.", flush=True)

if __name__ == "__main__":
    asyncio.run(run_pipeline())
