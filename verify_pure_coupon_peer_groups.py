import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    FloodWaitError, UsernameInvalidError, UsernameNotOccupiedError,
    ChannelPrivateError, ChannelInvalidError
)

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

SESSION_FILE = "froxy_session_output.txt"
with open(SESSION_FILE, "r", encoding="utf-8") as f:
    SESSION_STRING = f.read().strip()

# -------------------------------------------------------------
# 1. GOLD STANDARD SEEDS (FROM USER)
# -------------------------------------------------------------
USER_GOLD_SEEDS = [
    "kuponkodalimsatimm",
    "kuponyaticaret",
    "wishx_2",
    "kodkuponmarketi",
    "ceksatkupon2",
    "Kuponcekm",
    "kuponceking"
]

# -------------------------------------------------------------
# 2. EXCLUSIONS (Current active list & Blacklist)
# -------------------------------------------------------------
def get_excluded_list():
    excluded = set()
    if os.path.exists("gruplar.txt"):
        with open("gruplar.txt", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                u = line.strip().lower().lstrip("@")
                if u:
                    excluded.add(u)
    if os.path.exists("blacklist.txt"):
        with open("blacklist.txt", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                u = line.strip().lower().lstrip("@")
                if u:
                    excluded.add(u)
    print(f"[*] Hariç tutulan (Mevcut Liste + Kara Liste): {len(excluded)} grup", flush=True)
    return excluded

# -------------------------------------------------------------
# 3. PURE COUPON & CODE TRADING SIGNALS & NEGATIVE FILTERS
# -------------------------------------------------------------
COUPON_TRADE_SIGNALS = [
    "yemeksepeti", "yemek", "trendyol", "getir", "tıkla gelsin", "tiklagelsin",
    "migros", "money", "turna", "enuygun", "bilet", "pepsi", "kazandrio", "cips",
    "frebayt", "freebayt", "gb", "kod", "kupon", "çek", "cek", "indirim",
    "satılık", "alınır", "dm", "fiyat", "stok", "hesap", "chatgpt", "canva", "netflix",
    "lisans", "key", "ödeme", "havale", "papara", "iban", "güvenli", "aracı"
]

BETTING_TERMS = [
    "bahis", "casino", "slot", "sweet bonanza", "gates of olympus", "rulet",
    "blackjack", "iddaa", "tipster", "kupon tahmin", "maç tahmin", "oran şikesi",
    "bet", "deneme bonusu", "bonus veren", "pragmatic", "güvenilir bahis",
    "canlı bahis", "roll", "aviator", "zeplin"
]

SPAM_TERMS = [
    "cc mail", "carding", "warez", "crack", "escort", "porno", "lezbiyen",
    "ifsa", "ifşa", "+18", "illegal", "paneli patlat", "datacı", "muris"
]

ADMIN_ONLY_DEAL_TERMS = [
    "sıcak fırsatlar", "sicak firsatlar", "fırsat avcısı", "firsat avcisi",
    "amazon fırsat", "affiliate", "sadece admin paylaşır", "yalnızca admin",
    "mesaj yazmak yasaktır", "sohbete kapalı", "paylaşım kanalı", "duyuru kanalı"
]

async def verify_pure_groups():
    excluded = get_excluded_list()
    
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    me = await client.get_me()
    print(f"[+] Bağlandı: {me.first_name} (@{me.username}) | ID: {me.id}\n", flush=True)

    candidates = set()

    # Step 1: Load all archived candidates
    if os.path.exists("all_archived_coupon_groups.json"):
        with open("all_archived_coupon_groups.json", "r", encoding="utf-8") as f:
            archived = json.load(f)
            for u in archived:
                u_clean = u.lower().lstrip("@")
                if u_clean not in excluded:
                    candidates.add(u_clean)

    # Step 2: Harvest sibling links from user's 7 gold standard seed groups
    print(f"[*] Kullanıcının 7 Referans Grubunun son mesajlarından çapraz linkler çekiliyor...", flush=True)
    for seed in USER_GOLD_SEEDS:
        try:
            entity = await client.get_entity(seed)
            msgs = await client.get_messages(entity, limit=350)
            print(f"  -> Seed @{seed}: {len(msgs)} mesaj tarandı", flush=True)
            for m in msgs:
                if m and m.text:
                    for found in re.finditer(r"(?:t\.me/|@)([a-zA-Z0-9_]{4,32})", m.text):
                        u = found.group(1).lower()
                        if u not in excluded and u not in candidates and u not in {
                            "joinchat", "share", "proxy", "bot", "channel", "http", "https", "support",
                            "admin", "destek", "yardim", "iletisim", "reklam"
                        }:
                            candidates.add(u)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"Seed error @{seed}: {e}", flush=True)

    print(f"\n[*] Toplam Doğrulanacak Aday Sayısı: {len(candidates)}", flush=True)
    print(f"[*] 1'e 1 Canlı Mesaj & İçerik Denetimi Başlatılıyor...\n", flush=True)

    now = datetime.now(timezone.utc)
    verified_pure_groups = []

    for uname in sorted(list(candidates)):
        try:
            entity = await client.get_entity(uname)
            
            # 1. Must be supergroup / megagroup (Discussion group, NOT channel)
            is_broad = getattr(entity, 'broadcast', False)
            is_mega = getattr(entity, 'megagroup', False) or getattr(entity, 'gigagroup', False)
            if is_broad or not is_mega:
                continue

            title = getattr(entity, 'title', '') or ''
            title_lower = title.lower()

            # 2. Negative title filter
            if any(bt in title_lower for bt in BETTING_TERMS):
                continue
            if any(st in title_lower for st in SPAM_TERMS):
                continue
            if any(ad in title_lower for ad in ADMIN_ONLY_DEAL_TERMS):
                continue

            # 3. Pull Live Messages (Last 35 messages)
            messages = await client.get_messages(entity, limit=35)
            if not messages or len(messages) < 5:
                continue

            # 4. Freshness / Not Dead (Last message <= 48 hours)
            latest = messages[0]
            if not latest or not latest.date:
                continue
            msg_d = latest.date
            if msg_d.tzinfo is None:
                msg_d = msg_d.replace(tzinfo=timezone.utc)
            age_hours = (now - msg_d).total_seconds() / 3600.0
            
            if age_hours > 48.0:
                continue

            # 5. Multi-User Senders (Anti-Single Admin / Anti-Bot Broadcast)
            sample_msgs = messages[:30]
            senders = [m.sender_id for m in sample_msgs if m and m.sender_id]
            unique_senders = len(set(senders))
            
            if len(sample_msgs) >= 15 and unique_senders < 4:
                continue
            if len(sample_msgs) < 15 and unique_senders < 3:
                continue

            # 6. Analyze Live Chat Content for Pure Coupon/Food/Code Trading
            msg_texts = [m.text.lower() for m in messages if m and m.text]
            all_text_blob = " \n ".join(msg_texts)

            # Check betting in chat
            if any(bt in all_text_blob for bt in BETTING_TERMS):
                continue
            if any(st in all_text_blob for st in SPAM_TERMS):
                continue

            # Score positive coupon trade signals
            pos_matches = []
            for sig in COUPON_TRADE_SIGNALS:
                cnt = all_text_blob.count(sig)
                if cnt > 0:
                    pos_matches.append((sig, cnt))

            total_signal_score = sum(cnt for _, cnt in pos_matches)
            
            # Must have at least 4 coupon/code trade signals across messages
            if total_signal_score < 4:
                continue

            # Must contain specific food/coupon/code core words
            has_core_coupon = any(k in all_text_blob or k in title_lower for k in [
                "kupon", "çek", "cek", "kod", "yemeksepeti", "trendyol", "getir", "migros",
                "tıkla gelsin", "turna", "enuygun", "kazandrio", "pepsi", "gb", "hesap", "lisans"
            ])
            if not has_core_coupon:
                continue

            # Extract clean sample trading ads
            sample_ads = []
            for m in messages:
                if m and m.text and len(m.text) > 15:
                    clean_txt = " ".join(m.text.split())
                    if len(clean_txt) > 120:
                        clean_txt = clean_txt[:120] + "..."
                    if clean_txt not in sample_ads:
                        sample_ads.append(clean_txt)
                    if len(sample_ads) >= 3:
                        break

            # Categorize
            category = "Kupon, Çek & Kod Alım-Satım Pazarı"
            if any(k in all_text_blob or k in title_lower for k in ["yemeksepeti", "tıkla gelsin", "getir", "migros"]):
                category = "Yemeksepeti, Market & Yemek Kuponları"
            elif any(k in all_text_blob or k in title_lower for k in ["turna", "enuygun", "bilet"]):
                category = "Bilet, Seyahat & İndirim Kodları"
            elif any(k in all_text_blob or k in title_lower for k in ["pepsi", "kazandrio", "cips", "gb", "internet"]):
                category = "İnternet GB & Kapak/Cips Kodları"

            group_data = {
                "username": uname,
                "title": title,
                "category": category,
                "last_message_hours_ago": round(age_hours, 1),
                "unique_senders_last_30": unique_senders,
                "total_messages_inspected": len(messages),
                "coupon_signal_score": total_signal_score,
                "matched_signals": [p[0] for p in pos_matches[:8]],
                "sample_live_ads": sample_ads,
                "t_me_link": f"https://t.me/{uname}"
            }

            verified_pure_groups.append(group_data)
            print(f"[ONAYLANDI ✅ #{len(verified_pure_groups)}] @{uname} | {title[:28]} | Son Mesaj: {round(age_hours,1)}s | Gönderici: {unique_senders} | Skor: {total_signal_score}", flush=True)
            await asyncio.sleep(0.3)

        except FloodWaitError as e:
            print(f"[!] FloodWait: {e.seconds}s bekleniyor...", flush=True)
            await asyncio.sleep(e.seconds + 2)
        except (UsernameInvalidError, UsernameNotOccupiedError, ChannelPrivateError, ChannelInvalidError):
            pass
        except Exception:
            pass

    verified_pure_groups.sort(key=lambda x: (x["last_message_hours_ago"], -x["coupon_signal_score"]))

    print(f"\n=======================================================", flush=True)
    print(f"🎉 TOPLAM 1'E 1 BİREBİR KUPON/KOD GRUBU SAYISI: {len(verified_pure_groups)}", flush=True)
    print(f"=======================================================\n", flush=True)

    with open("birebir_saf_kupon_kod_gruplari.json", "w", encoding="utf-8") as f:
        json.dump(verified_pure_groups, f, ensure_ascii=False, indent=2)

    with open("birebir_saf_kupon_kod_gruplari.txt", "w", encoding="utf-8") as f:
        for g in verified_pure_groups:
            f.write(f"{g['username']}\n")

    print("[*] Kaydedildi: 'birebir_saf_kupon_kod_gruplari.json' ve 'birebir_saf_kupon_kod_gruplari.txt'", flush=True)
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(verify_pure_groups())
