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

# Comprehensive list of seed trade groups to harvest member ads & forwarded group links
SEED_GROUPS = [
    "kuponceksatis", "kuponhesapsatis", "kuponsat", "kuponkodalimsatimm",
    "kuponsatisgrup", "kuponsatimalim", "ceksatkupon", "Kuponcekm",
    "alimsatimmerkezii", "darktradehouse", "ticaretZ", "KodKuponMerkezi",
    "kodpazari", "YemekSepetiKuponu", "ceksatp8", "Minakuponkodsatis",
    "herkesibeklerimm", "kuponkodindirimilanlar", "bedavainternetkod",
    "alisverisforumuguncel", "kodkuponmarketi", "kuponsatislari0",
    "indirimkodusatis", "ticaretyapn", "ceksat", "kuponkodceksatis",
    "kuponkodhesapilan", "kuponindirimcek", "xAlimSatiim", "wishx_2",
    "satiskodtakasi", "kuponalsatgurup", "ceksatkupon2", "zeroticaret",
    "indirimkana", "indirim363", "kodmalf", "cek_kupon_kod_ilan",
    "kuponindirimkodalisveris", "kodalimsatim", "kodindirimsatis",
    "kuponkodalimsatim", "kuponhesap", "kuponkodalsat", "KuponindirimPazari",
    "ceksatistakasgrup", "kinseimedyaticaret", "kcksohbet", "dijitalticaretgrubu"
]

SEARCH_QUERIES = [
    # 1. Temel Kupon & Çek & Kod Aramaları
    "kupon alım satım", "kupon satışı", "kupon pazarı", "kupon borsa", "kupon market",
    "çek alım satım", "çek satışı", "çek pazarı", "çek borsa", "çek market", "çek bozdurma",
    "kod alım satım", "kod satışı", "kod pazarı", "kod borsa", "kod market", "kod deposu",
    "kupon kod alım satım", "kupon çek alım satım", "kod çek alım satım", "kupon kod ilan",
    "indirim kuponu alım satım", "promosyon kodu alım satım", "hediye çeki alım satım",
    "alışveriş çeki alım satım", "market çeki alım satım",
    
    # 2. Yemeksepeti & Yemek İndirim Kodları
    "yemeksepeti kupon", "yemeksepeti kod", "yemeksepeti indirim", "yemeksepeti hesap",
    "yemeksepeti ilk sipariş", "yemek kuponu alım satım", "yemek kodu alım satım",
    "tıkla gelsin kupon", "tıkla gelsin kod", "getir kupon", "getir yemek kupon",
    "aciktim kupon", "burger kupon", "dominos kupon",
    
    # 3. Market & Seyahat & Uçak Çekleri
    "migros çek", "migros kod", "migros money", "migros hediye çeki", "migros kupon",
    "turna çek", "turna uçak", "turna bilet", "enuygun çek", "enuygun uçak",
    "enuygun otobüs", "obilet kupon", "biletinial indirim", "sinema kupon",
    "havaist indirim", "tod tv kupon", "tod tv kod", "tod süperlig",
    
    # 4. İnternet Data & Kapak/Cips Promosyon Kodları
    "kapak kodu", "cips kodu", "pepsi kodu", "kazandrio kod", "daha daha kod",
    "freebayt internet", "frebayt puan", "internet data kod", "gb kod alım satım",
    "hediye kodu", "dijital kod alım satım", "dijital ürün alım satım"
]

EXCLUDE_WORDS = [
    # Oyunlar
    "brawl", "pes", "efootball", "e-football", "roblox", "pubg", "free fire", "valorant",
    "metin2", "zula", "lol", "fifa", "fc 24", "fc 25", "fc 26", "wolfteam", "growtopia",
    "standoff", "supercell", "fortnite", "clash of clans", "clash royale",
    # Trendyol Koleksiyon
    "koleksiyon", "paylaş kazan", "paylas kazan", "kaydetme", "takip et kazan", "koleksiyonum",
    # Bahis / Casino
    "iddaa", "bahis", "casino", "slot", "rulet", "canlı bahis", "rtp", "rexbet", "betroy",
    # Diğer İlgisiz
    "gayrimenkul", "emlak", "ev alım", "oto alım", "araba alım", "araç alım", "mining", "papara"
]

COUPON_TRADE_SIGNALS = [
    "yemeksepeti", "migros", "turna", "enuygun", "çek", "cek", "kupon", "kod",
    "indirim", "tıkla gelsin", "tiklagelsin", "getir", "hediye çeki", "hediye ceki",
    "kapak", "cips", "pepsi", "bilet", "tod", "gb", "internet", "daha daha",
    "kazandrio", "freebayt", "money", "satılık", "satıyorum", "alınır", "alıyorum",
    "fiyat", "tl", "₺", "stok", "dm", "ref", "takas", "devir"
]

async def collect_all_candidates(client):
    candidates = set()
    
    # 1. Add all seed groups
    for s in SEED_GROUPS:
        candidates.add(s.lower())
        
    # 2. Add candidates from all existing JSON/TXT files in workspace
    files = [
        "gruplar.txt", "auto_groups.txt", "scraped_groups.txt", "known_groups_dump.json",
        "master_known_blacklist.json", "yeni_onayli_gruplar_raporu.json",
        "nihai_onayli_yeni_satis_gruplari.json", "kupon_ozel_onayli_gruplar.json",
        "pure_account_code_approved.json", "birebir_yeni_kupon_kod_alimsatim_gruplari.json",
        "harvested_trade_groups.json", "ultimate_approved_groups.json",
        "food_code_gems_approved.json", "aktif_saf_kupon_kod_gruplari.json",
        "freshly_discovered_niche_groups.json", "nihai_saf_ticaret_pazarlari.json",
        "expanded_pure_trade_groups.json"
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
                                candidates.add(item.lower().lstrip("@"))
                            elif isinstance(item, dict):
                                u = item.get("username") or item.get("group")
                                if u:
                                    candidates.add(u.lower().lstrip("@"))
                    elif isinstance(d, dict):
                        for k, v in d.items():
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict) and "username" in item:
                                        candidates.add(item["username"].lower().lstrip("@"))
                                    elif isinstance(item, str):
                                        candidates.add(item.lower().lstrip("@"))
                            elif isinstance(k, str) and len(k) < 35:
                                candidates.add(k.lower().lstrip("@"))
            except Exception:
                pass
        elif fn.endswith(".txt"):
            try:
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        for m in re.finditer(r"([a-z0-9_]{4,32})", line.lower()):
                            candidates.add(m.group(1).lower())
            except Exception:
                pass

    print(f"[*] Başlangıç aday havuzu: {len(candidates)} grup")

    # 3. Harvest links from seed group message histories
    print("[*] Ana tohum grupların son 300 mesajındaki ilan linkleri taranıyor...")
    for seed in SEED_GROUPS:
        try:
            ent = await client.get_entity(seed)
            msgs = await client.get_messages(ent, limit=300)
            for m in msgs:
                if m and m.text:
                    for found in re.finditer(r"(?:t\.me/|@)([A-Za-z0-9_]{4,32})", m.text):
                        u = found.group(1).lower()
                        if u not in {"joinchat", "share", "proxy", "iv", "s", "c", "bot", "channel", "login", "signup"}:
                            candidates.add(u)
        except Exception:
            pass

    print(f"[*] Link hasadı sonrası toplam aday: {len(candidates)} grup")

    # 4. Search Telegram global directory for all queries
    print(f"[*] {len(SEARCH_QUERIES)} Arama Sorgusu ile Telegram Global Taraması Yapılıyor...")
    for idx, q in enumerate(SEARCH_QUERIES, 1):
        try:
            res = await client(SearchRequest(q=q, limit=50))
            new_c = 0
            for chat in res.chats:
                u = getattr(chat, 'username', None)
                if not u or getattr(chat, 'broadcast', False):
                    continue
                u_l = u.lower()
                if u_l not in candidates:
                    candidates.add(u_l)
                    new_c += 1
            print(f"[{idx:02d}/{len(SEARCH_QUERIES):02d}] '{q:26s}' -> +{new_c} yeni (Toplam: {len(candidates)})")
            await asyncio.sleep(1.0)
        except FloodWaitError as e:
            print(f"⚠️ FloodWait: {e.seconds}s...")
            await asyncio.sleep(e.seconds + 2)
        except Exception:
            pass

    return sorted(list(candidates))

async def test_and_filter_candidates(client, candidate_list):
    print(f"\n=======================================================")
    print(f"   100 ADET KUPON & KOD GRUBUNUN CANLI TEST DENETİMİ   ")
    print(f"   Test Edilecek Aday Sayısı: {len(candidate_list)}                     ")
    print(f"=======================================================\n")

    tested_approved = []
    now = datetime.now(timezone.utc)

    for idx, u in enumerate(candidate_list, 1):
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
            
            # TEST 1: Kanal / Broadcast Değil, SüperGrup Olmalı & Üye Sayısı >= 40
            if is_broad or not is_mega or members < 40:
                continue
                
            combined_meta = f"{title}\n{about}".lower()
            
            # TEST 2: Oyun Hesabı (PES, Brawl Stars vb.) ve Kumar/Bahis Olmamalı
            if any(ew in combined_meta for ew in EXCLUDE_WORDS):
                continue
                
            # TEST 3: Normal Üyelerin Mesaj Yazma İzni Açık Olmalı
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                continue
                
            # TEST 4: Son 35 Mesajın Çekilmesi ve İncelenmesi
            messages = await client.get_messages(entity, limit=35)
            if not messages:
                continue
                
            # TEST 5: Canlılık ve Son Mesaj Tarihi (Son 7 gün içinde aktif olmalı)
            latest_msg = messages[0]
            if not latest_msg or not latest_msg.date:
                continue
                
            msg_date = latest_msg.date
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
            age_hours = (now - msg_date).total_seconds() / 3600.0
            
            if age_hours > 168.0:  # 7 gün
                continue
                
            # TEST 6: Tek Taraflı Admin Yayını Değil, Çoklu Üye İlan Akışı Olmalı
            senders = [m.sender_id for m in messages if m and m.sender_id]
            unique_senders = len(set(senders))
            if len(messages) >= 12 and unique_senders < 3:
                continue
                
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            # TEST 7: Trendyol Koleksiyon Spamı Olmamalı
            if any(ew in combined_msgs for ew in ["koleksiyon kaydet", "koleksiyonuma tıkla", "paylaş kazan link"]):
                continue
                
            # TEST 8: Mesajlarda Oyun Hesabı Ağırlığı %18'den Az Olmalı
            game_msg_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in ["brawl", "pes", "pubg", "roblox", "valorant", "free fire"]))
            if len(msg_texts) > 0 and (game_msg_cnt / len(msg_texts)) > 0.18:
                continue
                
            # TEST 9: Pozitif Kupon, Çek, İndirim, Yemek, Turna, Kod Ticaret Sinyalleri
            signal_hits = [k for k in COUPON_TRADE_SIGNALS if k in combined_msgs + combined_meta]
            if len(signal_hits) < 2:
                continue
                
            # TEST 10: Canlı Alım-Satım İlan Örneklerinin Çıkarılması
            sample_ads = []
            for t in msg_texts:
                tl = t.lower()
                if any(k in tl for k in ["satılık", "satıyorum", "alınır", "alıyorum", "fiyat", "tl", "₺", "stok", "dm", "kupon", "kod", "çek", "cek", "yemeksepeti", "migros", "turna", "tod"]):
                    clean = t.replace("\n", " ").strip()
                    if len(clean) > 130:
                        clean = clean[:127] + "..."
                    if clean and len(sample_ads) < 3:
                        sample_ads.append(clean)
                        
            # Son aktiflik süresinin hesaplanması
            if age_hours < 1:
                last_active_str = f"{int(age_hours * 60)} dakika önce"
            elif age_hours < 24:
                last_active_str = f"{int(age_hours)} saat önce"
            else:
                last_active_str = f"{int(age_hours / 24)} gün önce"
                
            group_data = {
                "username": u,
                "title": title,
                "members": members,
                "slowmode_seconds": slowmode,
                "last_active": last_active_str,
                "age_hours": round(age_hours, 1),
                "unique_senders": unique_senders,
                "signals": signal_hits[:5],
                "about": about.replace("\n", " ")[:200],
                "sample_ads": sample_ads,
                "link": f"https://t.me/{u}"
            }
            tested_approved.append(group_data)
            print(f"[{len(tested_approved):03d}] 🎟️ ONAYLANDI: @{u:22s} | {title[:26]} | {members:5d} üye | Son Mesaj: {last_active_str}")
            
        except Exception:
            pass
        await asyncio.sleep(0.35)

    # Sort by recent activity and member count
    tested_approved.sort(key=lambda x: (x["age_hours"], -x["members"]))
    
    return tested_approved

async def main():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    candidates = await collect_all_candidates(client)
    approved_list = await test_and_filter_candidates(client, candidates)
    
    await client.disconnect()
    
    output = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total_tested_approved": len(approved_list),
        "groups": approved_list
    }
    
    with open("100_test_edilmis_onayli_kupon_gruplari.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print(f"\n=======================================================")
    print(f"✅ TÜM TESTLER TAMAMLANDI: Toplam {len(approved_list)} Kupon & Kod Grubu Onaylandı!")
    print(f"=======================================================\n")

if __name__ == '__main__':
    asyncio.run(main())
