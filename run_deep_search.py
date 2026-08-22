import asyncio
import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import ChatBannedRights

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
bot_token = '8961373302:AAGNs9fcPFU_XcWDUlhbNhQ2hRNzyRu6_MI'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

GAME_EXCLUDE_TERMS = [
    "brawl stars", "brawlstars", "pes", "efootball", "e-football", "roblox",
    "clash royale", "clash of clans", "pubg mobile", "free fire", "valorant hesap",
    "metin2", "zula", "lol hesap", "league of legends", "mobile legends", "mlbb",
    "fc 24", "fc 25", "fc 26", "fifa", "wolfteam", "growtopia"
]

CHAT_EXCLUDE_TERMS = [
    "sohbet grubu", "muhabbet", "tanışma", "arkadaşlık", "itiraf", "gırgır",
    "geyik", "liseli", "üniversite", "chat grubu", "sohbet & muhabbet"
]

ADMIN_DEAL_EXCLUDE_TERMS = [
    "sıcak fırsatlar", "sicak firsatlar", "fırsat avcısı", "firsat avcisi",
    "indirim haberleri", "günün fırsatları", "gunun firsatlari", "amazon fırsat",
    "affiliate", "sadece admin paylaşır", "yalnızca admin", "mesaj yazmak yasaktır",
    "sohbete kapalı", "paylaşım kanalı", "duyuru kanalı"
]

POSITIVE_TARGET_TERMS = [
    "kupon", "çek", "cek", "kod", "indirim kodu", "yemeksepeti", "trendyol",
    "getir", "migros", "hesap", "hesap satış", "hesap alım", "hesap alim",
    "lisans", "key", "windows", "office", "antivirüs", "dijital", "dijital ürün",
    "smm", "panel", "takipçi", "sosyal medya", "chatgpt", "canva", "adobe",
    "netflix", "spotify", "vpn", "freelance", "webmaster", "r10", "ticaret",
    "alım satım", "alim satim", "pazaryeri", "ilan"
]

def load_known():
    with open("known_groups_dump.json", "r", encoding="utf-8") as f:
        return set(json.load(f))

def clean_username(raw):
    raw = str(raw or "").strip()
    m = re.search(r"(?:t\.me/|telegram\.me/)?(?:joinchat/|\+)?([A-Za-z0-9_]{4,32})", raw)
    if m:
        u = m.group(1).lower()
        if u not in {"joinchat", "share", "addstickers", "proxy", "iv", "s", "c", "bot", "channel"}:
            return u
    return None

def search_duckduckgo(query, max_results=30):
    found = set()
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                # DDG wrapper link
                m = re.search(r"t\.me/([A-Za-z0-9_]{4,32})", href)
                if m:
                    u = clean_username(m.group(1))
                    if u:
                        found.add(u)
                text = a.text
                for m in re.finditer(r"t\.me/([A-Za-z0-9_]{4,32})", text):
                    u = clean_username(m.group(1))
                    if u:
                        found.add(u)
    except Exception as e:
        pass
    return found

def search_bing(query):
    found = set()
    url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code == 200:
            for m in re.finditer(r"t\.me/([A-Za-z0-9_]{4,32})", r.text):
                u = clean_username(m.group(1))
                if u:
                    found.add(u)
    except Exception:
        pass
    return found

def search_tg_directories(query):
    found = set()
    urls = [
        f"https://tlgrm.eu/channels?search={requests.utils.quote(query)}",
        f"https://telegramchannels.me/search?query={requests.utils.quote(query)}",
        f"https://tgstat.com/search?q={requests.utils.quote(query)}",
        f"https://telemetr.io/search?q={requests.utils.quote(query)}"
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            if r.status_code == 200:
                for m in re.finditer(r"t\.me/([A-Za-z0-9_]{4,32})", r.text):
                    u = clean_username(m.group(1))
                    if u:
                        found.add(u)
        except Exception:
            pass
    return found

SEARCH_QUERIES = [
    'site:t.me "kupon" "alım satım" telegram',
    'site:t.me "kupon sat" telegram grup',
    'site:t.me "çek sat" kupon telegram',
    'site:t.me "kod sat" indirim kuponu telegram',
    'site:t.me "hesap sat" dijital alım satım telegram',
    'site:t.me "hesap alım satım" telegram grup',
    'site:t.me "lisans satış" key telegram',
    'site:t.me "dijital ürün" satış ticaret telegram',
    'site:t.me "smm panel" ticaret grup telegram',
    'site:t.me "trendyol kupon" telegram grup',
    'site:t.me "yemeksepeti kupon" sat telegram',
    'site:t.me "canva" "chatgpt" hesap satış telegram',
    'site:t.me "netflix" "spotify" hesap satış telegram',
    'site:t.me "freelance" "ticaret" telegram grup',
    'site:t.me "webmaster" "alım satım" telegram',
    'site:t.me "sosyal medya" hesap satış telegram',
    'site:t.me "dijital pazar" alım satım telegram',
    'site:t.me "al sat" ticaret kupon telegram',
    'site:t.me "kod pazarı" alım satım telegram',
    'site:t.me "e-ticaret" alım satım telegram grup',
    '"t.me/" "kupon satış" grup',
    '"t.me/" "kod satışı" grup',
    '"t.me/" "hesap satış" ticaret',
    '"t.me/" "çek sat" grup',
    '"t.me/" "indirim kodu satış"',
    '"t.me/" "dijital ticaret" grup',
    '"t.me/" "smm alım satım"',
]

async def inspect_candidates(candidate_list, known_set):
    client = TelegramClient('group_scanner_bot', api_id, api_hash)
    await client.start(bot_token=bot_token)
    
    results = {
        "approved": [],
        "rejected": [],
        "errors": []
    }
    
    print(f"\n--- Telegram API ile {len(candidate_list)} Aday Taranıyor ---\n")
    
    for idx, username in enumerate(candidate_list, 1):
        if username in known_set:
            continue
            
        try:
            entity = await client.get_entity(username)
            full = await client(GetFullChannelRequest(entity))
            
            title = getattr(entity, 'title', '') or ''
            about = getattr(full.full_chat, 'about', '') or ''
            members = getattr(full.full_chat, 'participants_count', 0) or 0
            is_megagroup = getattr(entity, 'megagroup', False)
            is_broadcast = getattr(entity, 'broadcast', False)
            is_gigagroup = getattr(entity, 'gigagroup', False)
            
            combined_text = f"{title}\n{about}".lower()
            
            # Check 1: Must be a group, NOT a broadcast channel
            if is_broadcast or (not is_megagroup and not is_gigagroup):
                results["rejected"].append({
                    "username": username,
                    "title": title,
                    "members": members,
                    "reason": "Kanal / Broadcast (Grup değil, üyeler yazamaz)"
                })
                print(f"[{idx}/{len(candidate_list)}] ❌ @{username}: Kanal / Broadcast")
                continue
                
            # Check 2: Minimum members (e.g. at least 100 members)
            if members < 80:
                results["rejected"].append({
                    "username": username,
                    "title": title,
                    "members": members,
                    "reason": f"Çok az üye ({members} üye)"
                })
                print(f"[{idx}/{len(candidate_list)}] ❌ @{username}: Az üye ({members})")
                continue
                
            # Check 3: Check for excluded game categories (PES, Brawl Stars, etc.)
            game_hits = [term for term in GAME_EXCLUDE_TERMS if term in combined_text]
            if game_hits:
                results["rejected"].append({
                    "username": username,
                    "title": title,
                    "members": members,
                    "reason": f"Oyun hesabı grubu ({', '.join(game_hits)})"
                })
                print(f"[{idx}/{len(candidate_list)}] ❌ @{username}: Oyun hesabı ({game_hits})")
                continue
                
            # Check 4: Check for pure chat / sohbet
            chat_hits = [term for term in CHAT_EXCLUDE_TERMS if term in combined_text]
            # If title is explicitly just "sohbet" and no sales terms
            has_sales_terms = any(term in combined_text for term in POSITIVE_TARGET_TERMS)
            if (chat_hits and not has_sales_terms) or ("sohbet" in title.lower() and "satış" not in title.lower() and "alım" not in title.lower() and "ticaret" not in title.lower() and "kupon" not in title.lower() and "hesap" not in title.lower()):
                results["rejected"].append({
                    "username": username,
                    "title": title,
                    "members": members,
                    "reason": "Sohbet / Muhabbet grubu"
                })
                print(f"[{idx}/{len(candidate_list)}] ❌ @{username}: Sohbet grubu")
                continue
                
            # Check 5: Admin discount broadcast channel/group
            admin_hits = [term for term in ADMIN_DEAL_EXCLUDE_TERMS if term in combined_text]
            if admin_hits:
                results["rejected"].append({
                    "username": username,
                    "title": title,
                    "members": members,
                    "reason": f"Admin indirim/fırsat paylaşım grubu ({', '.join(admin_hits)})"
                })
                print(f"[{idx}/{len(candidate_list)}] ❌ @{username}: Admin fırsat/duyuru ({admin_hits})")
                continue
                
            # Check 6: Must have positive digital / coupon / code / account / license / commerce signals
            pos_hits = [term for term in POSITIVE_TARGET_TERMS if term in combined_text]
            if not pos_hits:
                results["rejected"].append({
                    "username": username,
                    "title": title,
                    "members": members,
                    "reason": "Dijital satış / kupon / hesap / ticaret sinyali bulunamadı"
                })
                print(f"[{idx}/{len(candidate_list)}] ❌ @{username}: Satış sinyali yok")
                continue
                
            # Check 7: Default banned rights (can regular members send messages?)
            banned_rights = getattr(full.full_chat, 'default_banned_rights', None)
            send_messages_restricted = False
            if banned_rights and getattr(banned_rights, 'send_messages', False):
                send_messages_restricted = True
                
            if send_messages_restricted:
                results["rejected"].append({
                    "username": username,
                    "title": title,
                    "members": members,
                    "reason": "Üyelerin mesaj gönderme yetkisi kapalı (Sadece Adminler yazabilir)"
                })
                print(f"[{idx}/{len(candidate_list)}] ❌ @{username}: Mesaj gönderme kapalı (Admin only)")
                continue

            # Determine category tags
            categories = []
            if any(t in combined_text for t in ["kupon", "çek", "cek", "yemeksepeti", "trendyol", "migros", "getir", "indirim kodu"]):
                categories.append("Kupon / Çek / Kod")
            if any(t in combined_text for t in ["hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "vpn", "mail", "gmail"]):
                categories.append("Hesap Satış")
            if any(t in combined_text for t in ["lisans", "key", "windows", "office", "yazılım", "script"]):
                categories.append("Lisans & Key & Yazılım")
            if any(t in combined_text for t in ["smm", "panel", "takipçi", "sosyal medya"]):
                categories.append("SMM & Sosyal Medya")
            if any(t in combined_text for t in ["ticaret", "alım satım", "pazaryeri", "ilan", "freelance", "webmaster"]):
                categories.append("Dijital Ticaret / Pazar")
                
            item = {
                "username": username,
                "title": title,
                "members": members,
                "about": about[:300],
                "categories": categories,
                "positive_signals": pos_hits,
                "link": f"https://t.me/{username}"
            }
            results["approved"].append(item)
            print(f"[{idx}/{len(candidate_list)}] ✅ UYGUN BULUNDU: @{username} | {title} ({members} üye) | Kat: {', '.join(categories)}")
            
        except Exception as e:
            err_str = str(e)
            results["errors"].append({"username": username, "error": err_str})
            print(f"[{idx}/{len(candidate_list)}] ⚠️ @{username} Hata: {err_str[:60]}")
            
        await asyncio.sleep(1.2)
        
    await client.disconnect()
    return results

def main():
    known_set = load_known()
    print(f"Mevcut bilinen grup sayısı (elenen): {len(known_set)}")
    
    candidates = set()
    print("Web ve Telegram dizin aramaları başlatılıyor...")
    for q in SEARCH_QUERIES:
        print(f"Arama yapılıyor: {q}")
        res1 = search_duckduckgo(q)
        res2 = search_bing(q)
        res3 = search_tg_directories(q)
        all_new = (res1 | res2 | res3) - known_set
        candidates.update(all_new)
        print(f"  Bulunan yeni adaylar: +{len(all_new)} (Toplam aday: {len(candidates)})")
        time.sleep(0.5)
        
    # Also test Turkish digital/coupon usernames pattern variations
    prefixes = [
        "kupon", "cek", "kod", "hesap", "lisans", "dijital", "smm", "ticaret", "alsat", "pazar", "market", "ilan"
    ]
    suffixes = [
        "satis", "satisi", "alimsatim", "pazari", "grubu", "tr", "turkiye", "merkezi", "dunyasi", "platformu", "alveri"
    ]
    for p in prefixes:
        for s in suffixes:
            u = f"{p}{s}"
            if u not in known_set:
                candidates.add(u)
            u2 = f"{p}_{s}"
            if u2 not in known_set:
                candidates.add(u2)
                
    candidates_list = sorted(list(candidates - known_set))
    print(f"\nToplam taranacak filtrelenmiş yeni aday sayısı: {len(candidates_list)}")
    
    results = asyncio.run(inspect_candidates(candidates_list, known_set))
    
    print("\n================ TARAMA VE İÇ DENETİM TAMAMLANDI ================\n")
    print(f"Uygun Bulunan Yeni Satış Grupları: {len(results['approved'])}")
    print(f"Reddedilen / Elenen Gruplar: {len(results['rejected'])}")
    
    with open("yeni_onayli_satis_gruplari.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print("Sonuçlar 'yeni_onayli_satis_gruplari.json' dosyasına kaydedildi.")

if __name__ == "__main__":
    main()
