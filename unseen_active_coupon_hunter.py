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

def build_complete_blacklist():
    blacklist = set()
    files = [
        "gruplar.txt", "auto_groups.txt", "scraped_groups.txt", "known_groups_dump.json",
        "master_known_blacklist.json", "yeni_onayli_gruplar_raporu.json", "yeni_onayli_gruplar_v2.json",
        "nihai_onayli_yeni_satis_gruplari.json", "kupon_ozel_onayli_gruplar.json",
        "pure_account_code_approved.json", "birebir_yeni_kupon_kod_alimsatim_gruplari.json",
        "harvested_trade_groups.json", "ultimate_approved_groups.json",
        "food_code_gems_approved.json", "aktif_saf_kupon_kod_gruplari.json"
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
                                blacklist.add(item.lower().lstrip("@"))
                            elif isinstance(item, dict):
                                u = item.get("username") or item.get("group")
                                if u:
                                    blacklist.add(u.lower().lstrip("@"))
                    elif isinstance(d, dict):
                        for k, v in d.items():
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict) and "username" in item:
                                        blacklist.add(item["username"].lower().lstrip("@"))
                                    elif isinstance(item, str):
                                        blacklist.add(item.lower().lstrip("@"))
                            elif isinstance(k, str) and len(k) < 35:
                                blacklist.add(k.lower().lstrip("@"))
            except Exception:
                pass
        elif fn.endswith(".txt"):
            try:
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        for m in re.finditer(r"([a-z0-9_]{4,32})", line.lower()):
                            blacklist.add(m.group(1).lower())
            except Exception:
                pass
    return blacklist

SEARCH_TERMS = [
    # 1. Yemeksepeti & Yemek İndirimleri
    "yemeksepeti indirim", "yemeksepeti firsat", "yemeksepeti pazar", "yemeksepeti ticaret",
    "yemeksepeti grup", "yemeksepeti al sat", "yemeksepeti paylasim", "yemek indirim kod",
    "yemek kuponlari", "tıklagelsin indirim", "tiklagelsin kupon", "getir yemek kupon",
    "getir indirim", "aciktim kupon", "burger kupon", "dominos kupon",
    
    # 2. Migros & Market Çekleri
    "migros indirim", "migros kod", "migros hediye ceki", "migros sanal market",
    "migros money kod", "migros kupon", "market ceki alim", "market ceki satis",
    "sok market kod", "a101 kod", "carrefoursa kod",
    
    # 3. Uçak, Otobüs & Bilet Çekleri
    "turna indirim", "turna bilet", "turna ucak", "enuygun ucak", "enuygun otobus",
    "enuygun kupon", "enuygun kod", "obilet kupon", "obilet indirim", "obilet kod",
    "biletinial kupon", "biletix kupon", "sinema bilet kod", "havaist indirim",
    
    # 4. Eğlence, TV & Dijital Yayın Kodları
    "tod tv indirim", "tod tv kod", "tod superlig", "bein connect kupon",
    "s sport plus kod", "s sport kupon", "exxen kupon", "blutv kupon",
    "gain kod", "tabii kod", "storytel kod", "spotify kod", "netflix kod",
    
    # 5. İnternet Data & Kapak/Cips Kodları
    "dahadaha puan", "dahadaha hak", "kazandrio puan", "kazandrio cips",
    "pepsi kapak kod", "cips serit kod", "freebayt internet", "frebayt puan",
    "turkcell gb kupon", "vodafone gb kupon", "turktelekom gb kupon",
    
    # 6. E-Ticaret & Hediye Çekleri (Koleksiyon Hariç)
    "hediye ceki al sat", "hediye ceki pazar", "hediye ceki borsa", "hediye ceki dukkani",
    "alisveris ceki al sat", "alisveris ceki satis", "alisveris kuponu al sat",
    "boyner kupon", "watsons kupon", "gratis kupon", "defacto kupon", "lcw kupon",
    
    # 7. Kod & Kupon Borsa / Depo / Pazar Birleşimleri
    "kuponborsasi", "kodborsasi", "cekborsasi", "kupondeposu", "koddeposu",
    "cekdeposu", "kuponkulubu", "kodkulubu", "cekkulubu", "kuponvadisi",
    "kodvadisi", "cekvadisi", "kupondiyari", "koddiyari", "cekdiyari",
    "kuponmerkezi", "kodmerkezi", "indirimmerkezi", "firsatmerkezi",
    "indirimvadisi", "firsatvadisi", "kampanyavadisi", "avantajpazari"
]

EXCLUDE_WORDS = [
    "brawl", "pes", "efootball", "e-football", "roblox", "pubg", "free fire", "valorant",
    "metin2", "zula", "lol", "fifa", "fc 24", "fc 25", "fc 26", "wolfteam", "growtopia",
    "koleksiyon", "paylaş kazan", "paylas kazan", "kaydetme", "takip et kazan", "koleksiyonum",
    "iddaa", "bahis", "casino", "slot", "rulet", "canlı bahis", "rtp",
    "sıcak fırsatlar", "fırsat avcısı", "günün fırsatları",
    "gayrimenkul", "emlak", "ev alım", "oto alım", "araba alım", "araç alım", "mining", "papara"
]

POSITIVE_COUPON_WORDS = [
    "yemeksepeti", "migros", "turna", "enuygun", "çek", "cek", "kupon", "kod",
    "indirim", "tıkla gelsin", "tiklagelsin", "getir", "hediye çeki", "hediye ceki",
    "kapak", "cips", "pepsi", "bilet", "tod", "gb", "internet", "daha daha",
    "kazandrio", "freebayt", "money", "satılık", "satıyorum", "alınır", "alıyorum"
]

async def hunt_unseen_groups():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    blacklist = build_complete_blacklist()
    print(f"[*] Tam Karaliste / Daha Önce Bilinen Toplam Grup: {len(blacklist)}")
    
    discovered = {}
    now = datetime.now(timezone.utc)
    
    print(f"[*] {len(SEARCH_TERMS)} Özel Terim ile Telegram Global Taraması Başlatılıyor...")
    for idx, kw in enumerate(SEARCH_TERMS, 1):
        try:
            res = await client(SearchRequest(q=kw, limit=50))
            new_cnt = 0
            for chat in res.chats:
                u = getattr(chat, 'username', None)
                if not u:
                    continue
                u_l = u.lower()
                if u_l in blacklist or getattr(chat, 'broadcast', False):
                    continue
                if u_l not in discovered:
                    discovered[u_l] = chat
                    new_cnt += 1
            print(f"[{idx:02d}/{len(SEARCH_TERMS):02d}] '{kw:24s}' -> +{new_cnt} yeni (Toplam benzersiz aday: {len(discovered)})")
            await asyncio.sleep(1.1)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 2)
        except Exception:
            pass

    print(f"\n[*] Toplam incelenecek yepyeni aday grup sayısı: {len(discovered)}")
    print("[*] Canlılık, son mesaj tarihi ve kupon ticaret denetimi yapılıyor...\n")
    
    approved = []
    
    for u_l, chat in discovered.items():
        u = getattr(chat, 'username', '')
        if not u:
            continue
        try:
            full = await client(GetFullChannelRequest(chat))
            full_chat = full.full_chat
            title = getattr(chat, 'title', '') or ''
            about = getattr(full_chat, 'about', '') or ''
            members = getattr(full_chat, 'participants_count', 0) or 0
            slowmode = getattr(full_chat, 'slowmode_seconds', 0) or 0
            is_megagroup = getattr(chat, 'megagroup', False) or getattr(chat, 'gigagroup', False)
            
            if getattr(chat, 'broadcast', False) or not is_megagroup or members < 60:
                continue
                
            combined_meta = f"{title}\n{about}".lower()
            if any(ew in combined_meta for ew in EXCLUDE_WORDS):
                continue
                
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                continue
                
            messages = await client.get_messages(chat, limit=35)
            if not messages:
                continue
                
            latest_msg = messages[0]
            if not latest_msg or not latest_msg.date:
                continue
                
            msg_date = latest_msg.date
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
                
            age_hours = (now - msg_date).total_seconds() / 3600.0
            
            # Must be active within last 72 hours
            if age_hours > 72.0:
                continue
                
            senders = [m.sender_id for m in messages if m and m.sender_id]
            unique_senders = len(set(senders))
            if len(messages) >= 12 and unique_senders <= 2:
                continue
                
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            if any(ew in combined_msgs for ew in ["koleksiyon kaydet", "koleksiyonuma tıkla", "paylaş kazan"]):
                continue
                
            game_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in ["brawl", "pes", "pubg", "roblox", "valorant", "free fire"]))
            if len(msg_texts) > 0 and (game_cnt / len(msg_texts)) > 0.20:
                continue
                
            signal_hits = [k for k in POSITIVE_COUPON_WORDS if k in combined_msgs + combined_meta]
            if len(signal_hits) < 2:
                continue
                
            sample_ads = []
            for t in msg_texts:
                tl = t.lower()
                if any(k in tl for k in ["satılık", "satıyorum", "alınır", "alıyorum", "fiyat", "tl", "₺", "stok", "dm", "kupon", "kod", "çek", "cek", "yemeksepeti", "migros", "turna"]):
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
                "age_hours": round(age_hours, 1),
                "signals": signal_hits,
                "about": about.replace("\n", " ")[:200],
                "sample_ads": sample_ads,
                "link": f"https://t.me/{u}"
            }
            approved.append(rec)
            print(f"🎯 YENİ ONAYLI GRUP: @{u:22s} | {title[:28]} | {members} üye | Son Mesaj: {last_active_str}")
        except Exception:
            pass
        await asyncio.sleep(0.4)

    await client.disconnect()
    
    approved.sort(key=lambda x: (x["age_hours"], -x["members"]))
    
    output = {
        "scan_time": now.isoformat(),
        "total_unseen_approved": len(approved),
        "groups": approved
    }
    
    with open("yep_yeni_kupon_gruplari_kesif.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print(f"\n=======================================================")
    print(f"✅ TARAMA BİTTİ: {len(approved)} Adet Daha Önce Hiç Görülmemiş Yepyeni Kupon Grubu!")
    print("=======================================================\n")

if __name__ == '__main__':
    asyncio.run(hunt_unseen_groups())
