import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

def build_strict_blacklist():
    bl = set()
    files = [
        "gruplar.txt", "auto_groups.txt", "scraped_groups.txt", "blacklist.txt",
        "known_groups_dump.json", "master_known_blacklist.json",
        "yeni_onayli_gruplar_raporu.json", "yeni_onayli_gruplar_v2.json",
        "nihai_onayli_yeni_satis_gruplari.json", "kupon_ozel_onayli_gruplar.json",
        "pure_account_code_approved.json", "birebir_yeni_kupon_kod_alimsatim_gruplari.json",
        "harvested_trade_groups.json", "ultimate_approved_groups.json",
        "food_code_gems_approved.json", "aktif_saf_kupon_kod_gruplari.json",
        "yep_yeni_kupon_gruplari_kesif.json", "derin_web_kesif_onayli.json",
        "web_scraped_candidates.json"
    ]
    for fn in files:
        if not os.path.exists(fn):
            continue
        if fn.endswith(".json"):
            try:
                with open(fn, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if isinstance(d, list):
                        for item in d:
                            if isinstance(item, str):
                                bl.add(item.lower().lstrip("@"))
                            elif isinstance(item, dict):
                                u = item.get("username") or item.get("group")
                                if u:
                                    bl.add(u.lower().lstrip("@"))
                    elif isinstance(d, dict):
                        for k, v in d.items():
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict) and "username" in item:
                                        bl.add(item["username"].lower().lstrip("@"))
                                    elif isinstance(item, str):
                                        bl.add(item.lower().lstrip("@"))
                            elif isinstance(k, str) and len(k) < 35:
                                bl.add(k.lower().lstrip("@"))
            except Exception:
                pass
        elif fn.endswith(".txt"):
            try:
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        for m in re.finditer(r"([a-z0-9_]{4,32})", line.lower()):
                            bl.add(m.group(1).lower())
            except Exception:
                pass
    return bl

# Active seed trade groups to harvest member ads & forwarded group links
SEED_TRADE_GROUPS = [
    "kuponceksatis", "kuponhesapsatis", "kuponsat", "kuponkodalimsatimm",
    "kuponsatisgrup", "kuponsatimalim", "ceksatkupon", "Kuponcekm",
    "alimsatimmerkezii", "darktradehouse", "ticaretZ", "KodKuponMerkezi",
    "kodpazari", "YemekSepetiKuponu", "ceksatp8", "Minakuponkodsatis"
]

NICHE_SEARCH_QUERIES = [
    # 1. Saf Dijital Pazar & Ticaret Grupları
    "dijital pazar alım satım", "dijital pazar yeri alım satım", "dijital ticaret grubu",
    "dijital ürün alım satım", "dijital varlık alım satım", "dijital borsa alım satım",
    "dijital market alım satım", "dijital dükkan alım satım",
    
    # 2. Hesap Alım Satım & Ticaret Pazarı (Oyun Hariç)
    "hesap alım satım ticaret", "hesap pazarı ticaret", "premium hesap alım satım",
    "sosyal medya ticaret grubu", "sosyal medya alım satım pazar", "instagram hesap ticaret",
    "tiktok hesap ticaret", "gmail pazar alım satım", "mail alım satım pazar",
    "sanal numara alım satım", "sms onay pazar", "smm pazar ticaret",
    
    # 3. Yazılım & Lisans & Key Ticareti
    "lisans alım satım pazar", "yazılım alım satım pazar", "key alım satım pazar",
    "script alım satım ticaret", "bot alım satım ticaret", "chatgpt plus ticaret",
    "canva pro ticaret", "adobe lisans ticaret",
    
    # 4. Kupon & Çek & Kod Alım Satım Platformları
    "kupon alım satım pazar", "çek alım satım pazar", "kod alım satım pazar",
    "hediye çeki ticaret", "market çeki ticaret", "yemeksepeti ticaret pazar",
    "yemek kuponu ticaret", "turna çek ticaret", "enuygun çek ticaret",
    "kapak kodu ticaret", "promosyon kodu ticaret"
]

EXCLUDE_WORDS = [
    # Oyunlar (Kesinlikle Yasak)
    "brawl", "pes", "efootball", "e-football", "roblox", "pubg", "free fire", "valorant",
    "metin2", "zula", "lol", "fifa", "fc 24", "fc 25", "fc 26", "wolfteam", "growtopia",
    "standoff", "supercell", "fortnite", "clash of clans", "clash royale",
    # Trendyol Koleksiyon (Kesinlikle Yasak)
    "koleksiyon", "paylaş kazan", "paylas kazan", "kaydetme", "takip et kazan", "koleksiyonum",
    # Kumar / Bahis
    "iddaa", "bahis", "casino", "slot", "rulet", "canlı bahis", "rtp", "rexbet", "betroy",
    # Admin Tek Taraflı Fırsat / Duyuru / Sıcak Fırsatlar (Kullanıcı mesaj atamaz veya admin link atar)
    "sıcak fırsatlar", "sicak firsatlar", "fırsat avcısı", "firsat avcisi", "günün fırsatları",
    "sadece admin", "yalnızca admin", "mesaj yazmak yasak", "sohbete kapalı",
    # Diğer
    "gayrimenkul", "emlak", "ev alım", "oto alım", "araba alım", "mining", "papara"
]

TRADE_SIGNAL_WORDS = [
    "kupon", "kod", "çek", "cek", "yemeksepeti", "migros", "turna", "enuygun",
    "tod", "hesap", "lisans", "key", "gmail", "smm", "panel", "takipçi", "numara",
    "sms onay", "cips", "pepsi", "daha daha", "tıkla gelsin", "getir", "hediye çeki",
    "freebayt", "chatgpt", "canva", "netflix", "spotify", "adobe"
]

BUY_SELL_INTENT_WORDS = [
    "satılık", "satıyorum", "satarım", "alınır", "alıyorum", "alırım",
    "fiyat", "tl", "₺", "stok", "dm", "pm", "aracı", "escrow", "ref",
    "güvence", "takas", "devir", "güncel fiyat", "toplu alım", "toplu satış"
]

async def run_pure_trade_harvester():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    blacklist = build_strict_blacklist()
    now = datetime.now(timezone.utc)
    print(f"[*] Master Karaliste Toplam Grup Sayısı: {len(blacklist)}")
    
    raw_candidates = {}
    
    # 1. Scrape links and forwards from 16 active seed trade groups (recent 250 messages each)
    print(f"\n[*] 1. {len(SEED_TRADE_GROUPS)} Aktif Ticaret Grubunun Mesajlarındaki İlan Linkleri Taranıyor...")
    for seed in SEED_TRADE_GROUPS:
        try:
            entity = await client.get_entity(seed)
            messages = await client.get_messages(entity, limit=250)
            for msg in messages:
                if msg and msg.text:
                    for m in re.finditer(r"(?:t\.me/|@)([A-Za-z0-9_]{4,32})", msg.text):
                        u = m.group(1).lower()
                        if u not in blacklist and u not in SEED_TRADE_GROUPS and u not in {"joinchat", "share", "proxy", "iv", "s", "c", "bot", "channel", "login", "signup"}:
                            if u not in raw_candidates:
                                raw_candidates[u] = "seed_mention"
        except Exception:
            pass
            
    print(f"    -> İlan linklerinden çıkarılan tekil aday: {len(raw_candidates)}")
    
    # 2. Targeted Global Telegram Search
    print(f"[*] 2. {len(NICHE_SEARCH_QUERIES)} Özel Ticaret Sorgusu ile Telegram Global Araması...")
    for idx, q in enumerate(NICHE_SEARCH_QUERIES, 1):
        try:
            res = await client(SearchRequest(q=q, limit=50))
            new_c = 0
            for chat in res.chats:
                u = getattr(chat, 'username', None)
                if not u or getattr(chat, 'broadcast', False):
                    continue
                u_l = u.lower()
                if u_l in blacklist:
                    continue
                if u_l not in raw_candidates:
                    raw_candidates[u_l] = "global_search"
                    new_c += 1
            print(f"[{idx:02d}/{len(NICHE_SEARCH_QUERIES):02d}] '{q:28s}' -> +{new_c} yeni (Toplam tekil aday: {len(raw_candidates)})")
            await asyncio.sleep(1.2)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 2)
        except Exception:
            pass

    print(f"\n[*] Toplam incelenecek ham aday grup sayısı: {len(raw_candidates)}")
    print("[*] 3. Sıkı Filtreleme: Admin Kanalı Değil Gerçek Ticaret Pazarı ve Üye Çeşitliliği Denetimi...\n")
    
    vetted_groups = []
    
    for idx, (u, source) in enumerate(raw_candidates.items(), 1):
        try:
            entity = await client.get_entity(u)
            full = await client(GetFullChannelRequest(entity))
            full_chat = full.full_chat
            
            title = getattr(entity, 'title', '') or ''
            about = getattr(full_chat, 'about', '') or ''
            members = getattr(full_chat, 'participants_count', 0) or 0
            slowmode = getattr(full_chat, 'slowmode_seconds', 0) or 0
            is_mega = getattr(entity, 'megagroup', False) or getattr(entity, 'gigagroup', False)
            is_broad = getattr(entity, 'broadcast', False)
            
            # Supergroup check & member count
            if is_broad or not is_mega or members < 70:
                continue
                
            combined_meta = f"{title}\n{about}".lower()
            if any(ew in combined_meta for ew in EXCLUDE_WORDS):
                continue
                
            # Member posting rights check
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                continue
                
            # Fetch recent 35 messages
            messages = await client.get_messages(entity, limit=35)
            if not messages:
                continue
                
            # Liveliness check: Last message date must be recent (within 48 hours)
            latest_msg = messages[0]
            if not latest_msg or not latest_msg.date:
                continue
                
            msg_date = latest_msg.date
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
            age_hours = (now - msg_date).total_seconds() / 3600.0
            
            if age_hours > 48.0:
                continue
                
            # --- STRICT SENDER DIVERSITY CHECK (FILTER OUT SINGLE-ADMIN DEAL CHANNELS) ---
            senders = [m.sender_id for m in messages if m and m.sender_id]
            unique_senders = len(set(senders))
            
            # If 35 messages come from only <= 6 people, it is an admin broadcast/deal channel or bot spam
            if len(messages) >= 15 and unique_senders < 7:
                continue
                
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            # Reject trendyol collection spam
            if any(ew in combined_msgs for ew in ["koleksiyon kaydet", "koleksiyonuma tıkla", "paylaş kazan link"]):
                continue
                
            # Reject game accounts (PES, Brawl Stars, PUBG, Roblox etc)
            game_msg_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in ["brawl", "pes", "pubg", "roblox", "valorant", "free fire"]))
            if len(msg_texts) > 0 and (game_msg_cnt / len(msg_texts)) > 0.15:
                continue
                
            # Must have positive trade signals
            signal_hits = [k for k in TRADE_SIGNAL_WORDS if k in combined_msgs + combined_meta]
            if len(signal_hits) < 2:
                continue
                
            # Must have active buy/sell intent words from diverse members
            intent_hits = [k for k in BUY_SELL_INTENT_WORDS if k in combined_msgs]
            if len(intent_hits) < 2:
                continue
                
            # Extract sample live buy/sell ads
            sample_ads = []
            for t in msg_texts:
                tl = t.lower()
                if any(k in tl for k in ["satılık", "satıyorum", "alınır", "alıyorum", "fiyat", "tl", "₺", "stok", "dm", "kupon", "kod", "çek", "hesap", "lisans"]):
                    clean = t.replace("\n", " ").strip()
                    if len(clean) > 130:
                        clean = clean[:127] + "..."
                    if clean and len(sample_ads) < 3:
                        sample_ads.append(clean)
                        
            if age_hours < 1:
                last_active_str = f"{int(age_hours * 60)} dakika önce"
            elif age_hours < 24:
                last_active_str = f"{int(age_hours)} saat önce"
            else:
                last_active_str = f"{int(age_hours / 24)} gün önce"
                
            rec = {
                "username": u,
                "title": title,
                "members": members,
                "slowmode_seconds": slowmode,
                "last_active": last_active_str,
                "unique_senders": unique_senders,
                "trade_signals": signal_hits[:4],
                "about": about.replace("\n", " ")[:200],
                "sample_ads": sample_ads,
                "link": f"https://t.me/{u}"
            }
            vetted_groups.append(rec)
            print(f"💎 ONAYLANDI (TİCARET PAZARI): @{u:22s} | {title[:26]} | {members:5d} üye | {unique_senders} tekil üye ilanı | Son Mesaj: {last_active_str}")
            
        except Exception:
            pass
        await asyncio.sleep(0.4)

    await client.disconnect()
    
    vetted_groups.sort(key=lambda x: -x["members"])
    
    output = {
        "timestamp": now.isoformat(),
        "total_approved": len(vetted_groups),
        "groups": vetted_groups
    }
    
    with open("nihai_saf_ticaret_pazarlari.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print(f"\n=======================================================")
    print(f"✅ BİTTİ: Toplam {len(vetted_groups)} Yepyeni, Aktif, Üyelerin İlan Paylaştığı Satış Pazarı!")
    print("=======================================================\n")

if __name__ == '__main__':
    asyncio.run(run_pure_trade_harvester())
