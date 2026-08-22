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

# Ultra-targeted Coupon, Voucher, Promo Code & Food/Shopping Deal Keywords
KUPON_SEARCH_KEYWORDS = [
    # Kupon Çeşitleri
    "kupon satış", "kupon satis", "kupon alım satım", "kupon alim satim",
    "kupon pazarı", "kupon pazari", "kupon borsası", "kupon borsasi",
    "kupon marketi", "kupon market", "kupon deposu", "kupon dükkanı",
    "kupon alsat", "kupon takas", "kupon merkezi", "kupon paylaşım",
    "kupon dünyası", "kupon evi", "kupon kulübü", "kuponcu",
    
    # Çek & Hediye Çeki
    "çek satış", "cek satis", "çek alım satım", "cek alim satim",
    "çek pazarı", "cek pazari", "çek borsası", "cek borsasi",
    "çek marketi", "çek market", "çek bozdurma", "çek takas",
    "hediye çeki", "hediye ceki", "alışveriş çeki", "market çeki",
    "çek deposu", "çek dünyası", "çek al sat", "ceksat",
    
    # Kod & Promosyon & İndirim Kodu
    "kod satış", "kod satis", "kod alım satım", "kod alim satim",
    "kod pazarı", "kod pazari", "kod borsası", "kod marketi",
    "kod al sat", "kod deposu", "kod takas", "indirim kodu satış",
    "indirim kuponu", "promosyon kodu", "kampanya kodu", "davet kodu",
    "kapak kodu", "cips kodu", "kod dünyası", "kod merkezi",
    
    # Yemeksepeti & Yemek Kuponları
    "yemeksepeti kupon", "yemeksepeti indirim", "yemeksepeti kod",
    "yemeksepeti hesap", "yemeksepeti ilk sipariş", "yemek kuponu",
    "yemeksepeti alım satım", "yemeksepeti satış", "yemeksepeti çek",
    
    # Trendyol & Getir & Migros & Marketler
    "trendyol kupon", "trendyol indirim", "trendyol yemek kupon",
    "trendyol market kupon", "trendyol çek", "trendyol kod",
    "trendyol paylaş kazan", "trendyol koleksiyon", "trendyol hesap",
    "getir kupon", "getir indirim", "getir yemek kupon", "getir büyük",
    "migros çek", "migros kupon", "migros hemen", "migros indirim",
    "migros kod", "migros money", "carrefour çek", "a101 kupon",
    
    # Alışveriş & Bilet & Seyahat Kuponları
    "alışveriş kupon", "alisveris kupon", "alışveriş çeki",
    "amazon hediye çeki", "hepsiburada kupon", "hepsiburada çek",
    "boyner çek", "boyner hediye çeki", "defacto çek", "lcw çek",
    "turna kupon", "turna kod", "obilet kupon", "biletinial indirim",
    "sinema bileti indirim", "tod tv kupon", "internet kod", "gb kodu"
]

GAME_TERMS = [
    "brawl stars", "brawlstars", "pes", "efootball", "e-football", "roblox",
    "clash royale", "clash of clans", "pubg mobile", "free fire", "valorant",
    "metin2", "zula", "lol", "fifa", "fc 24", "fc 25", "fc 26", "wolfteam",
    "growtopia", "standoff", "supercell", "pubg", "fortnite"
]

ADMIN_DEAL_TERMS = [
    "sıcak fırsatlar", "sicak firsatlar", "fırsat avcısı", "firsat avcisi",
    "indirim haberleri", "günün fırsatları", "gunun firsatlari", "amazon fırsat",
    "affiliate", "sadece admin paylaşır", "yalnızca admin", "mesaj yazmak yasaktır",
    "sohbete kapalı", "paylaşım kanalı", "duyuru kanalı", "fırsat kanalı"
]

KUPON_POSITIVE_SIGNALS = [
    "kupon", "çek", "cek", "kod", "yemeksepeti", "trendyol", "migros", "getir",
    "indirim", "fırsat", "promosyon", "kampanya", "hediye çeki", "kapak", "cips",
    "pepsi", "turna", "bilet", "sinema", "tod", "gb", "internet", "ilk sipariş",
    "tl", "₺", "satılık", "satıyorum", "alınır", "alıyorum", "fiyat", "stok", "dm"
]

def load_all_existing():
    known = set()
    files = [
        "known_groups_dump.json", "gruplar.txt", "auto_groups.txt", "scraped_groups.txt",
        "yeni_onayli_gruplar_raporu.json", "yeni_onayli_gruplar_v2.json", "nihai_onayli_yeni_satis_gruplari.json"
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
                                known.add(item.lower().lstrip("@"))
                            elif isinstance(item, dict):
                                u = item.get("username") or item.get("group")
                                if u:
                                    known.add(u.lower().lstrip("@"))
                    elif isinstance(d, dict):
                        for k, v in d.items():
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict) and "username" in item:
                                        known.add(item["username"].lower().lstrip("@"))
                            elif isinstance(k, str) and len(k) < 35:
                                known.add(k.lower().lstrip("@"))
            except Exception:
                pass
        elif fn.endswith(".txt"):
            try:
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip().lstrip("@").lower()
                        m = re.search(r"([a-z0-9_]{4,32})", line)
                        if m:
                            known.add(m.group(1).lower())
            except Exception:
                pass
    return known

async def run_kupon_search():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    known_groups = load_all_existing()
    print(f"[*] Bilinen/kayıtlı mevcut grup sayısı (elenenler): {len(known_groups)}")
    
    # Dialogs check
    async for d in client.iter_dialogs():
        if d.is_group or d.is_channel:
            u = getattr(d.entity, 'username', '')
            if u:
                known_groups.add(u.lower())

    discovered_chats = {}
    
    print(f"\n=======================================================")
    print(f"   KUPON & ÇEK & KOD HEDEF ARAMASI ({len(KUPON_SEARCH_KEYWORDS)} Kelime)    ")
    print(f"=======================================================\n")
    
    for idx, kw in enumerate(KUPON_SEARCH_KEYWORDS, 1):
        try:
            res = await client(SearchRequest(q=kw, limit=50))
            new_count = 0
            for chat in res.chats:
                u = getattr(chat, 'username', None)
                if not u:
                    continue
                u_lower = u.lower()
                if u_lower in known_groups:
                    continue
                if getattr(chat, 'broadcast', False):
                    continue
                    
                if u_lower not in discovered_chats:
                    discovered_chats[u_lower] = {
                        "username": u,
                        "chat": chat,
                        "keyword": kw
                    }
                    new_count += 1
            print(f"[{idx:02d}/{len(KUPON_SEARCH_KEYWORDS):02d}] '{kw:26s}' -> +{new_count} yeni kupon/kod adayı (Toplam: {len(discovered_chats)})")
            await asyncio.sleep(1.6)
        except FloodWaitError as e:
            print(f"⚠️ FloodWait: {e.seconds}s bekleniyor...")
            await asyncio.sleep(e.seconds + 2)
        except Exception as e:
            print(f"⚠️ Hata: {e}")
            await asyncio.sleep(1.5)

    print(f"\n=======================================================")
    print(f"   KUPON/KOD GRUPLARININ DERİN İÇ VE MESAJ DENETİMİ    ")
    print(f"   İncelenecek Yeni Kupon Adayı: {len(discovered_chats)}                      ")
    print(f"=======================================================\n")

    kupon_approved = []
    kupon_rejected = []

    for idx, (u_lower, item) in enumerate(discovered_chats.items(), 1):
        chat = item["chat"]
        u = item["username"]
        kw = item["keyword"]
        
        try:
            full = await client(GetFullChannelRequest(chat))
            full_chat = full.full_chat
            
            title = getattr(chat, 'title', '') or ''
            about = getattr(full_chat, 'about', '') or ''
            members = getattr(full_chat, 'participants_count', 0) or 0
            slowmode = getattr(full_chat, 'slowmode_seconds', 0) or 0
            is_megagroup = getattr(chat, 'megagroup', False) or getattr(chat, 'gigagroup', False)
            
            combined = f"{title}\n{about}".lower()
            
            # 1. Megagroup / Supergroup Check
            if getattr(chat, 'broadcast', False) or not is_megagroup:
                kupon_rejected.append({"username": u, "title": title, "reason": "Broadcast Kanal"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> KANAL")
                continue
                
            # 2. Üye Sayısı Kontrolü (>70)
            if members < 70:
                kupon_rejected.append({"username": u, "title": title, "reason": f"Az üye ({members})"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> AZ ÜYE ({members})")
                continue
                
            # 3. Yazma İzni Kontrolü
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                kupon_rejected.append({"username": u, "title": title, "reason": "Yazma izni kapalı"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> YAZMA İZNİ KAPALI")
                continue
                
            # 4. Oyun Hesapları (PES, Brawl Stars vb.) Kontrolü
            if any(gt in combined for gt in GAME_TERMS):
                kupon_rejected.append({"username": u, "title": title, "reason": "Oyun grubu"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> OYUN GRUBU")
                continue
                
            # 5. Admin Duyuru / Sıcak Fırsat Tek Taraflı Kanal Kontrolü
            if any(at in combined for at in ADMIN_DEAL_TERMS):
                kupon_rejected.append({"username": u, "title": title, "reason": "Admin fırsat/duyuru"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> ADMİN DUYURU KANALI")
                continue
                
            # 6. Grup İçi Mesaj Analizi
            try:
                messages = await client.get_messages(chat, limit=30)
            except Exception:
                messages = []
                
            if not messages:
                kupon_rejected.append({"username": u, "title": title, "reason": "Mesaj geçmişi yok"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> MESAJ YOK")
                continue
                
            # Tek Taraflı Admin Yayını mı?
            senders = [m.sender_id for m in messages if m and m.sender_id]
            if len(messages) >= 12 and len(set(senders)) <= 2:
                kupon_rejected.append({"username": u, "title": title, "reason": "Tek taraflı admin yayını"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> TEK TARAFLI YAYIN")
                continue
                
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            # Mesajlarda oyun hesabı oranı kontrolü
            game_msg_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in GAME_TERMS))
            if len(msg_texts) > 0 and (game_msg_cnt / len(msg_texts)) > 0.25:
                kupon_rejected.append({"username": u, "title": title, "reason": "Oyun hesap mesajları"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> OYUN HESAP MESAJLARI")
                continue
                
            # Kupon / Kod / Çek / İndirim Alım-Satım Sinyali
            kupon_hits = [k for k in ["kupon", "çek", "cek", "kod", "yemeksepeti", "trendyol", "migros", "getir", "indirim", "kapak", "cips", "turna", "bilet", "tod"] if k in combined_msgs + combined]
            if not kupon_hits:
                kupon_rejected.append({"username": u, "title": title, "reason": "Kupon/kod sinyali yok"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> KUPON SİNYALİ YOK")
                continue
                
            # Örnek İlanlar
            samples = []
            for t in msg_texts:
                tl = t.lower()
                if any(kh in tl for kh in ["kupon", "çek", "cek", "kod", "yemeksepeti", "trendyol", "migros", "getir", "indirim", "tl", "₺"]):
                    clean = t.replace("\n", " ").strip()
                    if len(clean) > 120:
                        clean = clean[:117] + "..."
                    if clean and len(samples) < 3:
                        samples.append(clean)
                        
            rec = {
                "username": u,
                "title": title,
                "members": members,
                "slowmode_seconds": slowmode,
                "kupon_signals": kupon_hits,
                "about": about.replace("\n", " ")[:200],
                "sample_ads": samples,
                "search_keyword": kw,
                "link": f"https://t.me/{u}"
            }
            kupon_approved.append(rec)
            print(f"[{idx:03d}/{len(discovered_chats):03d}] 🎯 ONAYLANDI (KUPON/KOD): @{u:20s} | {title[:28]} | {members} üye | {', '.join(kupon_hits[:4])}")

        except FloodWaitError as e:
            print(f"⚠️ FloodWait: {e.seconds}s bekleniyor...")
            await asyncio.sleep(e.seconds + 2)
        except Exception as e:
            print(f"⚠️ Hata (@{u}): {e}")

        await asyncio.sleep(1.2)

    await client.disconnect()
    
    kupon_approved.sort(key=lambda x: x["members"], reverse=True)
    
    output = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total_discovered": len(discovered_chats),
        "total_approved": len(kupon_approved),
        "total_rejected": len(kupon_rejected),
        "groups": kupon_approved
    }
    
    with open("kupon_ozel_onayli_gruplar.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print("\n=======================================================")
    print(f"✅ KUPON & KOD & ÇEK ÖZEL TARAMASI TAMAMLANDI!")
    print(f"Bulunan Yeni Onaylı Kupon/Kod Grubu: {len(kupon_approved)}")
    print("=======================================================\n")

if __name__ == '__main__':
    asyncio.run(run_kupon_search())
