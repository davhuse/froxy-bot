import asyncio
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, UsernameInvalidError, UsernameNotOccupiedError, ChannelPrivateError

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

# 1. Expanded search keywords focused strictly on digital sales, coupon, code, account, license, SMM
SEARCH_KEYWORDS = [
    # Kupon & Kod & Çek
    "kupon satış", "kupon satis", "kupon alım satım", "kupon alim satim",
    "çek satış", "cek satis", "çek alım satım", "cek alim satim",
    "kod satış", "kod satis", "indirim kodu satış", "indirim kuponu",
    "yemeksepeti kupon", "trendyol yemek kupon", "trendyol kupon", "getir kupon",
    "migros indirim", "kupon pazarı", "kupon pazari", "çek pazarı", "cek pazari",
    "kod pazarı", "kod pazari", "kupon takas", "kupon borsa", "çek bozdurma",
    
    # Dijital Hesap & Abonelik Satış
    "hesap satış", "hesap satis", "hesap alım satım", "hesap alim satim",
    "hesap pazarı", "hesap pazari", "dijital hesap", "premium hesap",
    "chatgpt hesap", "chatgpt plus", "canva pro", "canva hesap",
    "netflix hesap", "netflix 4k", "spotify premium", "youtube premium",
    "disney plus", "adobe cc", "adobe creative cloud", "gemini advanced",
    "claude pro", "perplexity pro", "semrush hesap", "nordvpn", "vpn hesap",
    "gmail hesap", "gmail alım satım", "eski gmail", "telegram hesap",
    "twitter hesap", "instagram hesap satış", "sosyal medya hesap",
    
    # Lisans & Key & Yazılım
    "lisans satış", "lisans satis", "lisans alım satım", "key satış", "key satis",
    "windows lisans", "windows key", "office 365 lisans", "office key",
    "antivirüs lisans", "kaspersky key", "yazılım satış", "script satış",
    "bot satış", "dijital ürün satış", "dijital tedarik",
    
    # SMM Panel & Sosyal Medya & Dijital Pazar
    "smm panel", "smm bayi", "smm ticaret", "smm pazar", "takipçi satış",
    "sosyal medya pazarı", "sosyal medya pazari", "dijital pazar", "dijital pazar yeri",
    "freelance pazar", "webmaster ticaret", "r10 ticaret", "e-ticaret alım satım"
]

# Exclusion Terms for Game Accounts
GAME_TERMS = [
    "brawl stars", "brawlstars", "pes", "efootball", "e-football", "roblox",
    "clash royale", "clash of clans", "pubg mobile", "free fire", "valorant",
    "metin2", "zula", "lol hesap", "league of legends", "mobile legends", "mlbb",
    "fc 24", "fc 25", "fc 26", "fifa", "wolfteam", "growtopia", "standoff",
    "supercell", "pubg", "fortnite"
]

# Exclusion Terms for Admin Deals / Broadcast
ADMIN_DEAL_TERMS = [
    "sıcak fırsatlar", "sicak firsatlar", "fırsat avcısı", "firsat avcisi",
    "indirim haberleri", "günün fırsatları", "gunun firsatlari", "amazon fırsat",
    "affiliate", "sadece admin paylaşır", "yalnızca admin", "mesaj yazmak yasaktır",
    "sohbete kapalı", "paylaşım kanalı", "duyuru kanalı"
]

# Positive Target Signals
POSITIVE_TERMS = [
    "kupon", "çek", "cek", "kod", "indirim", "yemeksepeti", "trendyol", "getir", "migros",
    "hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "gemini", "claude",
    "lisans", "key", "windows", "office", "antivirüs", "vpn", "smm", "panel",
    "takipçi", "sosyal medya", "dijital", "ticaret", "alım", "satım", "satış",
    "fiyat", "tl", "₺", "stok", "dm", "özelden", "teslim", "güvenli", "aracı"
]

def load_known_dump():
    known = set()
    if os.path.exists("known_groups_dump.json"):
        with open("known_groups_dump.json", "r", encoding="utf-8") as f:
            known = set(json.load(f))
    return known

def fold_text(text):
    text = unicodedata.normalize("NFKD", str(text or "")).casefold()
    return "".join(c for c in text if not unicodedata.combining(c))

async def run_search():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("HATA: Oturum yetkilendirilmedi!")
        return

    me = await client.get_me()
    print(f"✅ Bağlı Kullanıcı: {me.first_name} {me.last_name or ''} (@{me.username or 'yok'}) | ID: {me.id}")
    
    known_groups = load_known_dump()
    print(f"[*] Veritabanındaki bilinen/korumalı grup sayısı (elenenler): {len(known_groups)}")
    
    # Also get currently joined dialogs
    joined_usernames = set()
    async for d in client.iter_dialogs():
        if d.is_group or d.is_channel:
            u = getattr(d.entity, 'username', '')
            if u:
                joined_usernames.add(u.lower())
                known_groups.add(u.lower())
    print(f"[*] Hesabın üye olduğu grup/kanal sayısı: {len(joined_usernames)}\n")

    discovered_chats = {} # username -> chat object
    
    print(f"=======================================================")
    print(f"      1. TELEGRAM GLOBAL ARAMA BAŞLATILIYOR ({len(SEARCH_KEYWORDS)} Kelime)     ")
    print(f"=======================================================\n")
    
    for idx, kw in enumerate(SEARCH_KEYWORDS, 1):
        try:
            res = await client(SearchRequest(q=kw, limit=50))
            new_in_kw = 0
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
                    new_in_kw += 1
            print(f"[{idx:02d}/{len(SEARCH_KEYWORDS):02d}] '{kw:26s}' -> +{new_in_kw} yeni aday grup (Toplam tekil: {len(discovered_chats)})")
            await asyncio.sleep(1.8)
        except FloodWaitError as e:
            print(f"⚠️ FloodWait: {e.seconds} saniye bekleniyor...")
            await asyncio.sleep(e.seconds + 2)
        except Exception as e:
            print(f"⚠️ Hata ({kw}): {e}")
            await asyncio.sleep(2)

    print(f"\n=======================================================")
    print(f"      2. DERİN GRUP İÇİ MESAJ & KURAL ANALİZİ BAŞLADI  ")
    print(f"      Toplam İncelenecek Yeni Aday: {len(discovered_chats)}                    ")
    print(f"=======================================================\n")

    approved_groups = []
    rejected_groups = []

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
            is_broadcast = getattr(chat, 'broadcast', False)
            
            # KONTROL 1: Kanal mı?
            if is_broadcast or not is_megagroup:
                rejected_groups.append({"username": u, "title": title, "members": members, "reason": "Broadcast Kanal"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> KANAL (Reddedildi)")
                continue

            # KONTROL 2: Üye Sayısı Eşiği (> 100)
            if members < 100:
                rejected_groups.append({"username": u, "title": title, "members": members, "reason": f"Az üye ({members})"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> AZ ÜYE ({members})")
                continue

            # KONTROL 3: Mesaj Gönderme İzni
            banned_rights = getattr(full_chat, 'default_banned_rights', None)
            if banned_rights and getattr(banned_rights, 'send_messages', False):
                rejected_groups.append({"username": u, "title": title, "members": members, "reason": "Normal üyelerin yazma izni kapalı"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> YAZMA İZNİ KAPALI")
                continue

            # KONTROL 4: Açıklamada Admin İndirim / Duyuru Sinyali
            combined_about = f"{title}\n{about}".lower()
            admin_deal_hits = [t for t in ADMIN_DEAL_TERMS if t in combined_about]
            if admin_deal_hits:
                rejected_groups.append({"username": u, "title": title, "members": members, "reason": f"Admin fırsat/duyuru ({', '.join(admin_deal_hits)})"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> ADMİN FIRSAT KANALI")
                continue

            # KONTROL 5: GRUP İÇİ MESAJLARI ÇEK VE TARA
            try:
                messages = await client.get_messages(chat, limit=30)
            except Exception as e:
                messages = []

            if not messages:
                # Mesajlar çekilemediyse veya boşsa
                rejected_groups.append({"username": u, "title": title, "members": members, "reason": "Mesajlar okunamadı veya grup boş"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> MESAJ GEÇMİŞİ YOK")
                continue

            # Mesaj Gönderen Analizi (Sadece admin mi spamlıyor?)
            senders = [m.sender_id for m in messages if m and m.sender_id]
            unique_senders = len(set(senders))
            if len(messages) >= 15 and unique_senders <= 2:
                rejected_groups.append({"username": u, "title": title, "members": members, "reason": "Sadece 1-2 kişi/admin mesaj atıyor (Tek taraflı yayın)"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> TEK TARAFLI ADMİN YAYINI")
                continue

            # Mesaj İçerik Analizi
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            # Oyun Hesabı Analizi (PES, Brawl Stars vb.)
            game_msg_count = 0
            for text in msg_texts:
                t_lower = text.lower()
                if any(gt in t_lower for gt in GAME_TERMS):
                    game_msg_count += 1
                    
            if len(msg_texts) > 0 and (game_msg_count / len(msg_texts)) > 0.35:
                rejected_groups.append({"username": u, "title": title, "members": members, "reason": f"Ağırlıklı oyun hesabı ({game_msg_count}/{len(msg_texts)} mesaj)"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> OYUN HESAPLARI (PES/Brawl Stars vb.)")
                continue

            # Pozitif Satış Sinyalleri Analizi
            positive_signal_count = 0
            sale_samples = []
            for text in msg_texts:
                t_lower = text.lower()
                has_pos = any(pt in t_lower for pt in POSITIVE_TERMS)
                has_price_or_trade = bool(re.search(r"\b\d+\s*(?:tl|₺|tl'den|tl ye)\b", t_lower)) or any(k in t_lower for k in ["satılık", "satilik", "satıyorum", "satiyorum", "fiyat", "stok", "dm", "özelden", "alınır", "alinir"])
                if has_pos and has_price_or_trade:
                    positive_signal_count += 1
                    clean_s = text.replace("\n", " ").strip()
                    if len(clean_s) > 120:
                        clean_s = clean_s[:117] + "..."
                    if clean_s and len(sale_samples) < 3:
                        sale_samples.append(clean_s)

            # Eğer grup içi mesajlarda gerçek satış sinyali yoksa (örneğin sadece geyik/sohbet dönüyorsa)
            if positive_signal_count == 0 and not any(pt in combined_about for pt in ["kupon", "hesap", "lisans", "smm", "kod", "çek"]):
                rejected_groups.append({"username": u, "title": title, "members": members, "reason": "Satış ilanı bulunamadı (Genel Sohbet)"})
                print(f"[{idx:03d}/{len(discovered_chats):03d}] ❌ @{u:22s} -> SATIŞ İLANI YOK (Sohbet)")
                continue

            # Kategori Tespiti
            categories = []
            if any(t in combined_msgs + combined_about for t in ["kupon", "çek", "cek", "yemeksepeti", "trendyol", "migros", "getir", "indirim"]):
                categories.append("Kupon / Kod / Çek")
            if any(t in combined_msgs + combined_about for t in ["hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "vpn", "gmail"]):
                categories.append("Dijital Hesap Satış")
            if any(t in combined_msgs + combined_about for t in ["lisans", "key", "windows", "office", "yazılım", "script", "bot"]):
                categories.append("Lisans & Key & Yazılım")
            if any(t in combined_msgs + combined_about for t in ["smm", "panel", "takipçi", "sosyal medya"]):
                categories.append("SMM & Sosyal Medya")
            if not categories:
                categories.append("Dijital Ticaret / Pazar")

            approved_record = {
                "username": u,
                "title": title,
                "members": members,
                "categories": categories,
                "slowmode_seconds": slowmode,
                "about": about.replace("\n", " ")[:200],
                "sample_ads": sale_samples,
                "search_keyword": kw,
                "link": f"https://t.me/{u}"
            }
            approved_groups.append(approved_record)
            print(f"[{idx:03d}/{len(discovered_chats):03d}] 🎯 ONAYLANDI: @{u:20s} | {title[:28]} | {members} üye | {', '.join(categories)}")

        except FloodWaitError as e:
            print(f"⚠️ FloodWait: {e.seconds} saniye bekleniyor...")
            await asyncio.sleep(e.seconds + 2)
        except Exception as e:
            print(f"⚠️ Hata (@{u}): {e}")

        await asyncio.sleep(1.2)

    await client.disconnect()

    approved_groups.sort(key=lambda x: x["members"], reverse=True)
    
    final_output = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "account": f"+12237587384 (@{me.username or 'SosyalPazarSMM'})",
        "total_discovered": len(discovered_chats),
        "total_approved": len(approved_groups),
        "total_rejected": len(rejected_groups),
        "approved_groups": approved_groups
    }

    with open("yeni_onayli_gruplar_raporu.json", "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)

    print("\n=======================================================")
    print(f"✅ TARAMA VE İÇ DENETİM TAMAMLANDI!")
    print(f"Bulunan Uygun Yeni Satış Grubu: {len(approved_groups)}")
    print(f"Elenen Grup/Kanal Sayısı: {len(rejected_groups)}")
    print("=======================================================\n")

if __name__ == '__main__':
    asyncio.run(run_search())
