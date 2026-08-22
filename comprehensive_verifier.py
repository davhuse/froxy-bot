import json
import os
import re
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
import time
import concurrent.futures

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

# -------------------------------------------------------------
# 1. EXCLUSIONS (Current Blasting List & Hard Blacklist)
# -------------------------------------------------------------
def get_excluded():
    excluded = set()
    
    # 1. Currently active blasting list
    if os.path.exists("gruplar.txt"):
        with open("gruplar.txt", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                u = line.strip().lower().lstrip("@")
                if u:
                    excluded.add(u)
                    
    # 2. Blacklist
    if os.path.exists("blacklist.txt"):
        with open("blacklist.txt", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                u = line.strip().lower().lstrip("@")
                if u:
                    excluded.add(u)
                    
    print(f"[*] Hariç Tutulan (Mevcut Liste + Kara Liste) Sayısı: {len(excluded)}")
    return excluded

# -------------------------------------------------------------
# 2. GATHER CANDIDATES FROM ALL REPOSITORIES & EXTRACTS
# -------------------------------------------------------------
def gather_all_candidate_sources(excluded):
    candidates = set()
    
    files_to_check = [
        "scraped_groups.txt", "new_target_groups_found.txt", "extracted_raw_candidates.json",
        "grup_arama_sonuclari.json", "yeni_grup_sonuclari.json", "yeni_onayli_gruplar_v2.json",
        "yeni_onayli_gruplar_raporu.json", "food_code_gems_approved.json", "pure_account_code_approved.json",
        "derin_kesif_onayli_yeni_gruplar.json", "nihai_saf_ticaret_pazarlari.json",
        "web_scraped_candidates.json", "kesinlikle_yepyeni_kupon_gruplari.json"
    ]
    
    for fn in files_to_check:
        if not os.path.exists(fn):
            continue
        try:
            if fn.endswith(".json"):
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, str):
                                u = item.strip().lower().lstrip("@")
                                if 3 < len(u) < 35 and u not in excluded:
                                    candidates.add(u)
                            elif isinstance(item, dict):
                                for k in ["username", "group", "id", "chat_id"]:
                                    v = item.get(k)
                                    if v and isinstance(v, str):
                                        u = v.strip().lower().lstrip("@").replace("https://t.me/", "")
                                        if 3 < len(u) < 35 and u not in excluded:
                                            candidates.add(u)
                    elif isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(k, str) and 3 < len(k) < 35 and k not in excluded:
                                candidates.add(k.strip().lower().lstrip("@"))
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict):
                                        for subk in ["username", "group"]:
                                            subv = item.get(subk)
                                            if subv and isinstance(subv, str):
                                                u = subv.strip().lower().lstrip("@").replace("https://t.me/", "")
                                                if 3 < len(u) < 35 and u not in excluded:
                                                    candidates.add(u)
                                    elif isinstance(item, str):
                                        u = item.strip().lower().lstrip("@")
                                        if 3 < len(u) < 35 and u not in excluded:
                                            candidates.add(u)
            elif fn.endswith(".txt"):
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        for m in re.finditer(r"(?:t\.me/|@|^|\s)([a-zA-Z0-9_]{4,32})", line):
                            u = m.group(1).lower()
                            if u not in excluded and u not in {"joinchat", "share", "proxy", "http", "https", "true", "false", "none", "bot", "channel", "support"}:
                                candidates.add(u)
        except Exception:
            pass
            
    print(f"[*] Toplam Değerlendirilecek Ham Aday Sayısı: {len(candidates)}")
    return candidates

# -------------------------------------------------------------
# 3. STRICT RULES & VERIFICATION
# -------------------------------------------------------------
BETTING_TERMS = [
    "bahis", "casino", "slot", "sweet bonanza", "gates of olympus", "rulet",
    "blackjack", "iddaa", "tipster", "kupon tahmin", "maç tahmin", "oran şikesi",
    "bet", "deneme bonusu", "bonus veren", "pragmatic", "güvenilir bahis",
    "canlı bahis", "roll", "aviator", "zeplin", "canlibahis", "kripto sinyal", "forex", "binomo"
]

SPAM_ILLEGAL_TERMS = [
    "cc mail", "carding", "warez", "crack", "nulled", "escort", "porno", "lezbiyen",
    "gay", "ifsa", "ifşa", "tr ifsa", "yetiskin", "18+", "+18", "vip grup", "link tl",
    "illegal", "paneli patlat", "datacı", "muris", "gsm tc", "cc alım", "banka hesap",
    "hesap kiralama", "kiralık hesap", "papara kiralama", "ibrahim", "tosla"
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
    "indirim haberleri", "günün fırsatları", "haber kanalı"
]

POSITIVE_TERMS = [
    "kupon", "çek", "cek", "kod", "indirim", "yemeksepeti", "trendyol", "getir", "migros",
    "hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "gemini", "claude",
    "lisans", "key", "windows", "office", "antivirüs", "vpn", "smm", "panel",
    "takipçi", "sosyal medya", "dijital", "ticaret", "alım", "satım", "satış", "satis",
    "fiyat", "tl", "₺", "stok", "dm", "özelden", "teslim", "güvenli", "aracı", "ilan", "devir",
    "pazar", "market", "al sat", "tedarik", "shopier", "hizmet", "takas", "abone"
]

def check_group(username):
    url = f"https://t.me/{username}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    })
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
            if "If you have Telegram, you can view and join" not in html and "tgme_page_title" not in html:
                return None
                
            title_m = re.search(r'<div class="tgme_page_title"[^>]*><span[^>]*>(.*?)</span>', html, re.DOTALL)
            if not title_m:
                title_m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            title = title_m.group(1).strip() if title_m else ""
            
            extra_m = re.search(r'<div class="tgme_page_extra"[^>]*>(.*?)</div>', html, re.DOTALL)
            extra = extra_m.group(1).strip() if extra_m else ""
            
            desc_m = re.search(r'<div class="tgme_page_description"[^>]*>(.*?)</div>', html, re.DOTALL)
            if not desc_m:
                desc_m = re.search(r'<meta property="og:description" content="([^"]+)"', html)
            desc = desc_m.group(1).strip() if desc_m else ""
            
            title = re.sub(r'<[^>]+>', '', title).strip()
            desc = re.sub(r'<[^>]+>', ' ', desc).strip()
            
            is_group = "members" in extra.lower() or "üye" in extra.lower() or "online" in extra.lower()
            is_channel = "subscribers" in extra.lower() or "abone" in extra.lower()
            
            # RULE 1: Must be a GROUP (Community chat), NOT a single-admin channel, NOT a personal user
            if not is_group or is_channel:
                return None
                
            mem_m = re.search(r'([0-9\s]+)\s*(?:members|üye)', extra, re.IGNORECASE)
            members = 0
            if mem_m:
                members = int(re.sub(r'\s+', '', mem_m.group(1)))
                
            online_m = re.search(r'([0-9\s]+)\s*online', extra, re.IGNORECASE)
            online = 0
            if online_m:
                online = int(re.sub(r'\s+', '', online_m.group(1)))
                
            # RULE 2: NOT a DEAD group -> Must have at least 60 members and active online members
            if members < 60 or online < 2:
                return None
                
            combined_meta = f"{title}\n{desc}".lower()
            
            # RULE 3: Strict Negative Filtering (Bahis, İllegal, Oyun, Tek Admin İndirim Haber)
            if any(bt in combined_meta for bt in BETTING_TERMS):
                return None
            if any(st in combined_meta for st in SPAM_ILLEGAL_TERMS):
                return None
            if any(gt in combined_meta for gt in GAME_ACCOUNT_TERMS):
                return None
            if any(ad in combined_meta for ad in ADMIN_DEAL_TERMS):
                return None

            # RULE 4: Positive Target Match
            pos_matches = []
            for pt in POSITIVE_TERMS:
                cnt = combined_meta.count(pt)
                if cnt > 0:
                    pos_matches.append((pt, cnt))
                    
            relevance_score = sum(cnt for _, cnt in pos_matches)
            if relevance_score < 1:
                return None

            category = "Dijital Ticaret & Pazar"
            if any(k in combined_meta for k in ["kupon", "çek", "cek", "yemeksepeti", "trendyol", "getir", "migros"]):
                category = "Kupon & Çek & Kod Pazarı"
            elif any(k in combined_meta for k in ["lisans", "windows", "office", "antivirüs", "key", "kaspersky"]):
                category = "Lisans & Key & Yazılım"
            elif any(k in combined_meta for k in ["chatgpt", "canva", "netflix", "spotify", "hesap", "gmail"]):
                category = "Premium Hesap & Dijital Ürün"
            elif any(k in combined_meta for k in ["smm", "takipçi", "sosyal medya"]):
                category = "SMM & Sosyal Medya Hizmetleri"

            return {
                "username": username,
                "title": title,
                "category": category,
                "members": members,
                "online": online,
                "relevance_score": relevance_score,
                "matched_keywords": [p[0] for p in pos_matches[:8]],
                "about_description": desc[:200] if desc else "N/A",
                "t_me_link": f"https://t.me/{username}"
            }
    except Exception:
        return None

def main():
    excluded = get_excluded()
    candidates = gather_all_candidate_sources(excluded)
    
    print(f"\n[*] Canlı Doğrulama Başlatılıyor ({len(candidates)} Aday)...")
    
    approved = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        future_to_uname = {executor.submit(check_group, uname): uname for uname in candidates}
        checked_count = 0
        
        for future in concurrent.futures.as_completed(future_to_uname):
            checked_count += 1
            res = future.result()
            if res:
                approved.append(res)
                print(f"[ONAYLANDI ✅ #{len(approved)}] @{res['username']} | {res['title'][:26]} | Üye: {res['members']} (Online: {res['online']}) | Kat: {res['category']}", flush=True)

    # Sort by online users, members, and relevance
    approved.sort(key=lambda x: (-x["online"], -x["members"], -x["relevance_score"]))
    
    print(f"\n=======================================================")
    print(f"🎉 TOPLAM DOĞRULANMIŞ YENİ HEDEF GRUP SAYISI: {len(approved)}")
    print(f"=======================================================\n")
    
    with open("yeni_birebir_hedef_gruplar.json", "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)

    with open("yeni_birebir_hedef_gruplar.txt", "w", encoding="utf-8") as f:
        for g in approved:
            f.write(f"{g['username']}\n")

    print("[*] Kaydedildi: 'yeni_birebir_hedef_gruplar.json' ve 'yeni_birebir_hedef_gruplar.txt'")

if __name__ == "__main__":
    main()
