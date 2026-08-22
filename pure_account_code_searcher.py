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

SEARCH_KEYWORDS_PURE = [
    # 1. Hesap Satış & Pazarı
    "hesap satış", "hesap satis", "hesap alım satım", "hesap alim satim",
    "hesap pazarı", "hesap pazari", "hesap borsası", "dijital hesap satış",
    "premium hesap", "hesap al sat", "hesap dükkanı", "hesap marketi",
    
    # 2. AI & Yazılım & Lisans Hesapları
    "chatgpt hesap", "chatgpt plus", "chatgpt satış", "canva pro",
    "canva hesap", "canva lisans", "adobe cc", "adobe hesap",
    "adobe lisans", "gemini advanced", "claude pro", "semrush hesap",
    "capcut pro", "midjourney hesap", "envato elements", "freepik premium",
    "windows lisans", "windows key", "windows 11 key", "office 365 lisans",
    "office key", "kaspersky key", "antivirüs key", "script satış",
    
    # 3. Streaming & VPN Hesapları
    "netflix hesap", "netflix 4k", "spotify premium", "spotify hesap",
    "youtube premium", "disney plus hesap", "nordvpn", "vpn hesap",
    
    # 4. Mail, Sosyal Medya & Platform Hesapları
    "gmail hesap satış", "gmail alım satım", "gmail pazar", "gmail ticaret",
    "eski tarihli hesap", "facebook hesap satış", "instagram hesap satış",
    "instagram hesap satılık", "telegram hesap satış", "twitter hesap satış",
    "sosyal medya hesap", "sanal numara", "sms onay",
    
    # 5. Kod & Çek & Dijital Ticaret (Trendyol Koleksiyon Hariç)
    "kod satış", "kod alım satım", "kod pazarı", "kod borsası",
    "kupon alım satım", "kupon alim satim", "çek alım satım", "cek alim satim",
    "çek satış", "cek satis", "çek bozdurma", "yemeksepeti kupon",
    "yemeksepeti ilk sipariş", "migros çek", "getir kupon", "turna çek",
    "tıkla gelsin kupon", "dijital ürün satış", "dijital pazar",
    
    # 6. SMM Panel & Dijital Hizmet Ticareti
    "smm panel", "smm ticaret", "smm bayi", "smm pazar",
    "takipçi satış", "sosyal medya pazarı", "freelance ticaret"
]

TRENDYOL_KOLEKSIYON_EXCLUDE = [
    "koleksiyon", "paylaş kazan", "paylas kazan", "kaydetme", "takip et kazan",
    "koleksiyonum", "koleksiyonu"
]

GAME_EXCLUDE = [
    "brawl stars", "brawlstars", "pes", "efootball", "e-football", "roblox",
    "clash royale", "clash of clans", "pubg mobile", "free fire", "valorant",
    "metin2", "zula", "lol", "fifa", "fc 24", "fc 25", "fc 26", "wolfteam",
    "growtopia", "standoff", "supercell", "pubg", "fortnite"
]

ADMIN_DEAL_EXCLUDE = [
    "sıcak fırsatlar", "sicak firsatlar", "fırsat avcısı", "firsat avcisi",
    "indirim haberleri", "günün fırsatları", "gunun firsatlari", "amazon fırsat",
    "affiliate", "sadece admin paylaşır", "yalnızca admin", "mesaj yazmak yasaktır",
    "sohbete kapalı", "paylaşım kanalı", "duyuru kanalı"
]

SPORTS_BET_EXCLUDE = [
    "iddaa", "bahis", "casino", "slot", "rulet", "canlı bahis", "oran", "rtp",
    "rexbet", "betroy", "bonus veren siteler", "freespin"
]

def load_all_existing():
    known = set()
    files = [
        "known_groups_dump.json", "gruplar.txt", "auto_groups.txt", "scraped_groups.txt",
        "yeni_onayli_gruplar_raporu.json", "yeni_onayli_gruplar_v2.json",
        "nihai_onayli_yeni_satis_gruplari.json", "kupon_ozel_onayli_gruplar.json"
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

async def run_pure_search():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    known_groups = load_all_existing()
    print(f"[*] Bilinen/korumalı mevcut grup sayısı: {len(known_groups)}")
    
    discovered = {}
    
    print(f"\n=======================================================")
    print(f"   KOD / KUPON / HESAP SATIŞ TİCARET ARAMASI ({len(SEARCH_KEYWORDS_PURE)} Kelime)  ")
    print(f"=======================================================\n")
    
    for idx, kw in enumerate(SEARCH_KEYWORDS_PURE, 1):
        try:
            res = await client(SearchRequest(q=kw, limit=50))
            new_c = 0
            for chat in res.chats:
                u = getattr(chat, 'username', None)
                if not u:
                    continue
                u_lower = u.lower()
                if u_lower in known_groups:
                    continue
                if getattr(chat, 'broadcast', False):
                    continue
                if u_lower not in discovered:
                    discovered[u_lower] = {
                        "username": u,
                        "chat": chat,
                        "keyword": kw
                    }
                    new_c += 1
            print(f"[{idx:02d}/{len(SEARCH_KEYWORDS_PURE):02d}] '{kw:26s}' -> +{new_c} yeni hedef aday (Toplam: {len(discovered)})")
            await asyncio.sleep(1.6)
        except FloodWaitError as e:
            print(f"⚠️ FloodWait: {e.seconds}s...")
            await asyncio.sleep(e.seconds + 2)
        except Exception as e:
            print(f"⚠️ Hata ({kw}): {e}")
            await asyncio.sleep(1.5)

    print(f"\n=======================================================")
    print(f"   GRUP İÇİ DERİN MESAJ & İLAN ANALİZİ                 ")
    print(f"   İncelenecek Yeni Ticaret Adayı: {len(discovered)}                  ")
    print(f"=======================================================\n")

    pure_approved = []
    pure_rejected = []

    for idx, (u_lower, item) in enumerate(discovered.items(), 1):
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
            
            # 1. Kanal / Broadcast Check
            if getattr(chat, 'broadcast', False) or not is_megagroup:
                pure_rejected.append({"username": u, "title": title, "reason": "Broadcast Kanal"})
                continue
                
            # 2. Üye Sayısı (> 80)
            if members < 80:
                pure_rejected.append({"username": u, "title": title, "reason": f"Az üye ({members})"})
                continue
                
            # 3. Trendyol Koleksiyon / Kaydetme / Paylaş Kazan Filtresi (İstenmeyen)
            if any(tk in combined for tk in TRENDYOL_KOLEKSIYON_EXCLUDE):
                pure_rejected.append({"username": u, "title": title, "reason": "Trendyol Koleksiyon / Kaydetme Grubu (Elenmiştir)"})
                print(f"[{idx:03d}/{len(discovered):03d}] ❌ @{u:22s} -> TRENDYOL KOLEKSİYON (Elenmiştir)")
                continue
                
            # 4. Oyun Hesapları (PES, Brawl Stars vb.) Filtresi
            if any(gt in combined for gt in GAME_EXCLUDE):
                pure_rejected.append({"username": u, "title": title, "reason": "Oyun hesabı grubu"})
                print(f"[{idx:03d}/{len(discovered):03d}] ❌ @{u:22s} -> OYUN HESABI GRUBU")
                continue
                
            # 5. Bahis / İddaa / Casino Filtresi
            if any(bt in combined for bt in SPORTS_BET_EXCLUDE):
                pure_rejected.append({"username": u, "title": title, "reason": "Bahis / İddaa grubu"})
                print(f"[{idx:03d}/{len(discovered):03d}] ❌ @{u:22s} -> BAHİS / İDDAA")
                continue
                
            # 6. Admin Tek Taraflı Fırsat/Duyuru Filtresi
            if any(at in combined for at in ADMIN_DEAL_EXCLUDE):
                pure_rejected.append({"username": u, "title": title, "reason": "Admin fırsat/duyuru"})
                continue
                
            # 7. Yazma İzni Kontrolü
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                pure_rejected.append({"username": u, "title": title, "reason": "Mesaj yazma izni kapalı"})
                continue
                
            # 8. Mesaj Geçmişi Analizi
            try:
                messages = await client.get_messages(chat, limit=30)
            except Exception:
                messages = []
                
            if not messages:
                pure_rejected.append({"username": u, "title": title, "reason": "Mesaj geçmişi yok"})
                continue
                
            senders = [m.sender_id for m in messages if m and m.sender_id]
            if len(messages) >= 12 and len(set(senders)) <= 2:
                pure_rejected.append({"username": u, "title": title, "reason": "Tek taraflı admin yayını"})
                continue
                
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            # Mesajlarda koleksiyon veya oyun spamı var mı?
            if any(tk in combined_msgs for tk in ["koleksiyon kaydet", "koleksiyonuma tıkla", "paylaş kazan link"]):
                pure_rejected.append({"username": u, "title": title, "reason": "Koleksiyon spam grubu"})
                continue
                
            game_msg_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in GAME_EXCLUDE))
            if len(msg_texts) > 0 and (game_msg_cnt / len(msg_texts)) > 0.25:
                pure_rejected.append({"username": u, "title": title, "reason": "Oyun hesap mesajları"})
                continue
                
            # Pozitif Kod / Kupon / Hesap / Lisans / SMM Sinyalleri
            pos_hits = [k for k in ["hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "gemini", "vpn", "gmail", "lisans", "key", "windows", "office", "kupon", "çek", "cek", "kod", "yemeksepeti", "migros", "smm", "panel", "takipçi", "ticaret", "alım satım", "satılık"] if k in combined_msgs + combined]
            if not pos_hits:
                pure_rejected.append({"username": u, "title": title, "reason": "Satış/ticaret sinyali yok"})
                continue
                
            samples = []
            for t in msg_texts:
                tl = t.lower()
                if any(kh in tl for kh in ["satılık", "fiyat", "tl", "₺", "stok", "dm", "hesap", "lisans", "kupon", "kod", "çek"]):
                    clean = t.replace("\n", " ").strip()
                    if len(clean) > 120:
                        clean = clean[:117] + "..."
                    if clean and len(samples) < 3:
                        samples.append(clean)
                        
            # Kategori
            cats = []
            if any(k in combined_msgs + combined for k in ["hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "vpn", "gmail", "mail"]):
                cats.append("Dijital Hesap Satış")
            if any(k in combined_msgs + combined for k in ["lisans", "key", "windows", "office", "yazılım", "script", "bot"]):
                cats.append("Lisans & Key & Yazılım")
            if any(k in combined_msgs + combined for k in ["kupon", "çek", "cek", "kod", "yemeksepeti", "migros", "turna", "tıkla gelsin"]):
                cats.append("Kupon & Kod & Çek Ticareti")
            if any(k in combined_msgs + combined for k in ["smm", "panel", "takipçi", "sosyal medya"]):
                cats.append("SMM & Sosyal Medya")
            if not cats:
                cats.append("Dijital Ticaret / Pazar")
                
            rec = {
                "username": u,
                "title": title,
                "members": members,
                "slowmode_seconds": slowmode,
                "categories": cats,
                "about": about.replace("\n", " ")[:200],
                "sample_ads": samples,
                "search_keyword": kw,
                "link": f"https://t.me/{u}"
            }
            pure_approved.append(rec)
            print(f"[{idx:03d}/{len(discovered):03d}] 🎯 ONAYLANDI (TİCARET): @{u:20s} | {title[:28]} | {members} üye | {', '.join(cats)}")

        except FloodWaitError as e:
            print(f"⚠️ FloodWait: {e.seconds}s...")
            await asyncio.sleep(e.seconds + 2)
        except Exception as e:
            print(f"⚠️ Hata: {e}")

        await asyncio.sleep(1.2)

    await client.disconnect()
    
    pure_approved.sort(key=lambda x: x["members"], reverse=True)
    
    output = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total_discovered": len(discovered),
        "total_approved": len(pure_approved),
        "total_rejected": len(pure_rejected),
        "groups": pure_approved
    }
    
    with open("pure_account_code_approved.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print("\n=======================================================")
    print(f"✅ SAF HESAP & KOD & KUPON & LİSANS SATIŞ TARAMASI TAMAMLANDI!")
    print(f"Bulunan Yeni Onaylı Ticaret Grubu: {len(pure_approved)}")
    print("=======================================================\n")

if __name__ == '__main__':
    asyncio.run(run_pure_search())
