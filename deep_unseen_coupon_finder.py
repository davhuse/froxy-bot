import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import InputPeerEmpty, InputMessagesFilterEmpty
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

def build_complete_historical_blacklist():
    bl = set()
    files = [
        "gruplar.txt", "auto_groups.txt", "scraped_groups.txt", "blacklist.txt",
        "known_groups_dump.json", "master_known_blacklist.json",
        "yeni_onayli_gruplar_raporu.json", "yeni_onayli_gruplar_v2.json",
        "nihai_onayli_yeni_satis_gruplari.json", "kupon_ozel_onayli_gruplar.json",
        "pure_account_code_approved.json", "birebir_yeni_kupon_kod_alimsatim_gruplari.json",
        "harvested_trade_groups.json", "ultimate_approved_groups.json",
        "food_code_gems_approved.json", "aktif_saf_kupon_kod_gruplari.json",
        "freshly_discovered_niche_groups.json", "nihai_saf_ticaret_pazarlari.json",
        "expanded_pure_trade_groups.json", "100_kesin_onayli_kupon_kod_gruplari.json",
        "100_tam_test_edilmis_kupon_ve_kod_gruplari.json", "100_kupon_kod_gruplar_listesi.txt",
        "canli_mesaj_onayli_kupon_gruplari.json", "canli_kupon_gruplari.txt"
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

# 37 Known Active Seed Trade Groups to crawl forwards and referenced partner communities
SEED_GROUPS = [
    "kuponhesapsatis", "kuponalsatgurup", "ceksatkupon", "kuponyaticaret",
    "minakuponkodsatis", "kuponkodceksatis", "kuponsatisgrup", "kuponkodalimsatimm",
    "kodkuponmarketi", "kuponsatislari0", "kodindirimsatis", "kuponkodualsat",
    "ticaretz", "xalimsatiim", "satiskodtakasi", "herkesibeklerimm",
    "kuponkodindirimilanlar", "bedavainternetkodalimsatim", "bedavainternetkod",
    "kuponkodhesapilan", "kuponindirimcek", "kodmalf", "kodalimsatim",
    "zeroticaret", "alimsatimmerkezii", "ceksat", "cek_kupon_kod_ilan",
    "kuponindirimkodalisveris", "alisverisforumuguncel", "kuponcekm",
    "indirimkodusatis", "ticaretyapn", "kodkuponmerkezi", "ceksatkupon2",
    "indirimkana", "indirim363", "ticaretgruptr"
]

# Deeper and unexplored transaction queries
DEEP_QUERIES = [
    "yemeksepeti indirim kupon", "yemeksepeti 250", "yemeksepeti ilk siparis",
    "yemeksepeti onay", "yemeksepeti numara", "yemeksepeti teslim", "yemeksepeti aciktim",
    "tıklagelsin indirim", "tiklagelsin 200", "tiklagelsin hesap", "getir kupon satılık",
    "migros sanal market kod", "migros money puan", "migros 100", "migros 200", "migros 500",
    "carrefoursa hediye çeki", "a101 hediye çeki", "şok market hediye çeki", "bim hediye çeki",
    "boyner hediye çeki", "lcw hediye çeki", "defacto hediye çeki", "gratis hediye çeki",
    "turna 600", "turna 300", "turna uçak bileti", "turna otobüs bileti", "turna indirim çeki",
    "enuygun uçak kupon", "enuygun otobüs kupon", "enuygun 250", "enuygun 500", "enuygun 1000",
    "biletix indirim", "biletinial selfy", "sinema kuponu satılık", "martı kupon satılık",
    "tod tv taraftar", "tod tv süper lig", "tod 3 ay", "tod 12 ay", "s sport plus 1 ay",
    "steam cüzdan kod", "valorant vp satılık", "pubg uc satılık", "google play kod satılık",
    "razer gold kod satılık", "bynogame kupon satılık", "itemci bakiye satılık",
    "salla kazan gb", "sil süpür gb", "çark gb", "paycell puan satılık", "tosla kupon satılık",
    "kupon takas", "kod takas", "çek takas", "kupon bozdurma", "çek bozdurma", "kod bozdurma"
]

EXCLUDE_WORDS = [
    "brawl", "pes", "efootball", "e-football", "roblox", "pubg", "free fire", "valorant",
    "koleksiyon", "paylaş kazan", "paylas kazan", "kaydetme", "takip et kazan", "koleksiyonum",
    "iddaa", "bahis", "casino", "slot", "rulet", "bet", "bonus", "kumar",
    "gayrimenkul", "emlak", "oto alım", "araba alım", "mining", "papara"
]

async def hunt_strictly_unseen_groups():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    blacklist = build_complete_historical_blacklist()
    print(f"[*] Tam Karaliste / Daha Önce Bilinen Toplam Grup: {len(blacklist)}")
    
    candidate_usernames = set()
    
    # 1. Crawl forwards & mention links from 37 seed groups (400 messages each = ~14,800 messages)
    print(f"[*] 1. {len(SEED_GROUPS)} Tohum Grubun Mesajlarındaki İleri İletilen (Forward) ve Partner Grup Linkleri Taranıyor...")
    for s in SEED_GROUPS:
        try:
            ent = await client.get_entity(s)
            msgs = await client.get_messages(ent, limit=400)
            for m in msgs:
                if not m:
                    continue
                # Check forwards
                fwd = m.fwd_from
                if fwd and fwd.from_id:
                    cid = getattr(fwd.from_id, 'channel_id', None) or getattr(fwd.from_id, 'chat_id', None)
                    if cid:
                        try:
                            fwd_ent = await client.get_entity(fwd.from_id)
                            u = getattr(fwd_ent, 'username', None)
                            if u and u.lower() not in blacklist:
                                candidate_usernames.add(u.lower())
                        except:
                            pass
                # Check text mentions
                if m.text:
                    for found in re.finditer(r"(?:t\.me/|@)([A-Za-z0-9_]{4,32})", m.text):
                        u = found.group(1).lower()
                        if u not in blacklist and u not in {"joinchat", "share", "proxy", "iv", "s", "c", "bot", "channel", "login", "signup"}:
                            candidate_usernames.add(u)
        except Exception:
            pass
            
    print(f"    -> İleri iletilen & bahsedilen yeni tekil grup adayı: {len(candidate_usernames)}")
    
    # 2. Deep Global Message Searches
    print(f"[*] 2. {len(DEEP_QUERIES)} Derin Canlı Mesaj Arama Sorgusu ile Telegram Taraması...")
    for idx, q in enumerate(DEEP_QUERIES, 1):
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
            
            new_in_q = 0
            for c in res.chats:
                u = getattr(c, 'username', None)
                if not u:
                    continue
                u_l = u.lower()
                is_mega = getattr(c, 'megagroup', False)
                is_broad = getattr(c, 'broadcast', False)
                if is_broad or not is_mega:
                    continue
                if u_l not in blacklist and u_l not in candidate_usernames:
                    candidate_usernames.add(u_l)
                    new_in_q += 1
            print(f"[{idx:02d}/{len(DEEP_QUERIES):02d}] '{q:28s}' -> +{new_in_q} yeni (Toplam benzersiz aday: {len(candidate_usernames)})")
            await asyncio.sleep(1.0)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 2)
        except Exception:
            pass

    print(f"\n[*] Toplam incelenecek yepyeni aday sayısı: {len(candidate_usernames)}")
    print("[*] 3. Canlılık, son mesaj tarihi ve kupon ticaret denetimi yapılıyor...\n")
    
    approved_unseen_groups = []
    now = datetime.now(timezone.utc)
    
    for u in sorted(list(candidate_usernames)):
        try:
            ent = await client.get_entity(u)
            full = await client(GetFullChannelRequest(ent))
            full_chat = full.full_chat
            
            title = getattr(ent, 'title', '') or ''
            about = getattr(full_chat, 'about', '') or ''
            members = getattr(full_chat, 'participants_count', 0) or 0
            slowmode = getattr(full_chat, 'slowmode_seconds', 0) or 0
            is_mega = getattr(ent, 'megagroup', False) or getattr(ent, 'gigagroup', False)
            is_broad = getattr(ent, 'broadcast', False)
            
            if is_broad or not is_mega or members < 40:
                continue
                
            combined_meta = f"{title}\n{about}".lower()
            if any(ew in combined_meta for ew in EXCLUDE_WORDS):
                continue
                
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                continue
                
            messages = await client.get_messages(ent, limit=25)
            if not messages:
                continue
                
            latest = messages[0]
            if not latest or not latest.date:
                continue
                
            msg_d = latest.date
            if msg_d.tzinfo is None:
                msg_d = msg_d.replace(tzinfo=timezone.utc)
            age_h = (now - msg_d).total_seconds() / 3600.0
            
            # Active within last 72 hours
            if age_h > 72.0:
                continue
                
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            if any(ew in combined_msgs for ew in ["koleksiyon kaydet", "koleksiyonuma tıkla", "paylaş kazan"]):
                continue
                
            game_msg_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in ["brawl", "pes", "pubg", "roblox", "valorant"]))
            if len(msg_texts) > 0 and (game_msg_cnt / len(msg_texts)) > 0.20:
                continue
                
            # Check coupon / trade signals
            if not any(k in combined_msgs + combined_meta for k in ["kupon", "kod", "çek", "cek", "yemeksepeti", "migros", "turna", "tod", "pepsi", "cips", "indirim", "fiyat", "tl", "₺", "satılık", "satıyorum", "alınır", "alıyorum", "hediye çeki", "bilet"]):
                continue
                
            samples = []
            for t in msg_texts:
                tl = t.lower()
                if any(k in tl for k in ["satılık", "satıyorum", "alınır", "alıyorum", "fiyat", "tl", "₺", "stok", "dm", "kupon", "kod", "çek", "yemeksepeti", "migros", "turna", "tod"]):
                    clean = t.replace("\n", " ").strip()
                    if len(clean) > 130:
                        clean = clean[:127] + "..."
                    if clean and len(samples) < 3:
                        samples.append(clean)
                        
            if age_h < 1:
                last_active_str = f"{int(age_h * 60)} dakika önce"
            elif age_h < 24:
                last_active_str = f"{int(age_h)} saat önce"
            else:
                last_active_str = f"{int(age_h / 24)} gün önce"
                
            rec = {
                "username": u,
                "title": title,
                "members": members,
                "slowmode_seconds": slowmode,
                "last_active": last_active_str,
                "age_hours": round(age_h, 1),
                "about": about.replace("\n", " ")[:200],
                "sample_ads": samples,
                "link": f"https://t.me/{u}"
            }
            approved_unseen_groups.append(rec)
            print(f"🎯 YENİ BULUNAN KUPON GRUBU: @{u:22s} | {title[:28]} | {members:5d} üye | Son Mesaj: {last_active_str}")
            
        except Exception:
            pass
        await asyncio.sleep(0.3)
        
    await client.disconnect()
    
    approved_unseen_groups.sort(key=lambda x: (x["age_hours"], -x["members"]))
    
    with open("kesinlikle_yepyeni_kupon_gruplari.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_new_approved": len(approved_unseen_groups),
            "groups": approved_unseen_groups
        }, f, ensure_ascii=False, indent=2)
        
    print(f"\n=======================================================")
    print(f"✅ TARAMA BİTTİ: Toplam {len(approved_unseen_groups)} Adet Daha Önce Hiç Görülmemiş Yepyeni Kupon Grubu!")
    print(f"=======================================================\n")

if __name__ == '__main__':
    asyncio.run(hunt_strictly_unseen_groups())
