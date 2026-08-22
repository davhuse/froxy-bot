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
# 1. EXCLUSIONS (Current Active Blasting List & Blacklist)
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
# 2. GATHER ALL CANDIDATES
# -------------------------------------------------------------
def gather_candidates(excluded):
    candidates = set()
    
    files = [
        "all_archived_coupon_groups.json",
        "100_kesin_onayli_kupon_kod_gruplari.json",
        "100_kesin_onayli_kupon_ve_kod_gruplari.json",
        "100_onayli_test_edilmis_kupon_gruplari.json",
        "100_tam_dogrulanmis_kupon_kod_gruplari.json",
        "100_tam_test_edilmis_kupon_ve_kod_gruplari.json",
        "aktif_saf_kupon_kod_gruplari.json",
        "canli_mesaj_onayli_kupon_gruplari.json",
        "kupon_ozel_onayli_gruplar.json",
        "birebir_yeni_kupon_kod_alimsatim_gruplari.json",
        "food_code_gems_approved.json",
        "pure_account_code_approved.json",
        "derin_kesif_onayli_yeni_gruplar.json",
        "derin_web_kesif_onayli.json",
        "kesinlikle_yepyeni_kupon_gruplari.json",
        "yep_yeni_kupon_gruplari_kesif.json",
        "nihai_saf_ticaret_pazarlari.json",
        "extracted_raw_candidates.json",
        "scraped_groups.txt"
    ]
    
    for fn in files:
        if not os.path.exists(fn):
            continue
        try:
            if fn.endswith(".json"):
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                    items = []
                    if isinstance(data, list):
                        items = data
                    elif isinstance(data, dict):
                        if "groups" in data and isinstance(data["groups"], list):
                            items = data["groups"]
                        elif "approved_groups" in data and isinstance(data["approved_groups"], list):
                            items = data["approved_groups"]
                        else:
                            for k, v in data.items():
                                if isinstance(k, str) and 3 < len(k) < 35:
                                    if k.lower().lstrip("@") not in excluded:
                                        candidates.add(k.lower().lstrip("@"))
                                if isinstance(v, list):
                                    items.extend(v)
                    for item in items:
                        if isinstance(item, dict):
                            uname = item.get("username") or item.get("group")
                            if uname and isinstance(uname, str):
                                u_clean = uname.strip().lower().lstrip("@")
                                if 3 < len(u_clean) < 35 and u_clean not in excluded:
                                    candidates.add(u_clean)
                        elif isinstance(item, str):
                            u_clean = item.strip().lower().lstrip("@")
                            if 3 < len(u_clean) < 35 and u_clean not in excluded:
                                candidates.add(u_clean)
            elif fn.endswith(".txt"):
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        for m in re.finditer(r"(?:t\.me/|@|^|\s)([a-zA-Z0-9_]{4,32})", line):
                            u = m.group(1).lower()
                            if u not in excluded and u not in {"joinchat", "share", "proxy", "http", "https", "true", "false", "none", "bot", "channel", "support"}:
                                candidates.add(u)
        except Exception:
            pass
            
    print(f"[*] Toplam Değerlendirilecek Aday Sayısı: {len(candidates)}", flush=True)
    return candidates

# -------------------------------------------------------------
# 3. STRICT COUPON / CODE / VOUCHER MATCHING & NEGATIVE FILTERS
# -------------------------------------------------------------
BETTING_TERMS = [
    "bahis", "casino", "slot", "sweet bonanza", "gates of olympus", "rulet",
    "blackjack", "iddaa", "tipster", "kupon tahmin", "maç tahmin", "oran şikesi",
    "bet", "deneme bonusu", "bonus veren", "pragmatic", "güvenilir bahis",
    "canlı bahis", "roll", "aviator", "zeplin", "canlibahis", "kripto", "forex"
]

SPAM_TERMS = [
    "cc mail", "carding", "warez", "crack", "nulled", "escort", "porno", "lezbiyen",
    "gay", "ifsa", "ifşa", "tr ifsa", "yetiskin", "18+", "+18", "vip grup", "link tl",
    "illegal", "paneli patlat", "datacı", "muris", "gsm tc", "cc alım", "banka hesap",
    "hesap kiralama", "kiralık hesap", "papara kiralama"
]

GAME_TERMS = [
    "brawl stars", "brawlstars", "clash royale", "clash of clans", "pes mobile",
    "efootball", "free fire", "wolfteam", "growtopia", "standoff", "supercell",
    "mobile legends", "mlbb"
]

ADMIN_DEAL_TERMS = [
    "sıcak fırsatlar", "sicak firsatlar", "fırsat avcısı", "firsat avcisi",
    "amazon fırsat", "affiliate", "sadece admin paylaşır", "yalnızca admin",
    "mesaj yazmak yasaktır", "sohbete kapalı", "paylaşım kanalı", "duyuru kanalı",
    "indirim haberleri", "günün fırsatları", "indirimde al", "indirim paylaşımları",
    "haber kanalı"
]

COUPON_POSITIVE_TERMS = [
    "kupon", "çek", "cek", "kod", "yemeksepeti", "trendyol", "getir", "tıkla gelsin",
    "tiklagelsin", "migros", "money", "turna", "enuygun", "bilet", "pepsi", "kazandrio",
    "cips", "frebayt", "freebayt", "gb", "internet", "hediye çeki", "market çeki",
    "indirim", "kampanya", "satılık", "alınır", "alım", "satım", "takas", "pazar", "ticaret"
]

def check_coupon_group(username):
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
            
            # RULE 1: Must be a GROUP (Community trading chat), NOT a single-admin channel, NOT a personal user
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
                
            # RULE 2: NOT DEAD -> Must have members >= 60 and online >= 2
            if members < 60 or online < 2:
                return None
                
            combined_meta = f"{title}\n{desc}".lower()
            
            # RULE 3: Strict Negative Filtering (Bahis, İllegal, Oyun, Tek Admin İndirim Haber)
            if any(bt in combined_meta for bt in BETTING_TERMS):
                return None
            if any(st in combined_meta for st in SPAM_TERMS):
                return None
            if any(gt in combined_meta for gt in GAME_ACCOUNT_TERMS):
                return None
            if any(ad in combined_meta for ad in ADMIN_DEAL_TERMS):
                return None

            # RULE 4: Strict Positive Match for Coupon/Code/Voucher Trading
            pos_matches = []
            for pt in COUPON_POSITIVE_TERMS:
                cnt = combined_meta.count(pt)
                if cnt > 0:
                    pos_matches.append((pt, cnt))
                    
            relevance_score = sum(cnt for _, cnt in pos_matches)
            if relevance_score < 1:
                return None
                
            # Must contain at least one explicit coupon/code/food/gift/voucher term in title or description
            has_explicit_term = any(k in combined_meta for k in [
                "kupon", "çek", "cek", "kod", "yemeksepeti", "trendyol", "getir", "migros",
                "tıkla gelsin", "turna", "enuygun", "kazandrio", "pepsi", "gb", "internet",
                "hediye çeki", "market çeki", "al-sat", "alım satım", "pazar", "ticaret", "hesap"
            ])
            if not has_explicit_term:
                return None

            category = "Kupon, Çek & Kod Alım-Satım Pazarı"
            if any(k in combined_meta for k in ["yemeksepeti", "tıkla gelsin", "getir", "migros"]):
                category = "Yemeksepeti, Market & Yemek Kuponları"
            elif any(k in combined_meta for k in ["turna", "enuygun", "bilet"]):
                category = "Bilet, Seyahat & İndirim Kodları"
            elif any(k in combined_meta for k in ["pepsi", "kazandrio", "cips", "gb", "internet"]):
                category = "İnternet GB, Kapak & Çekiliş Kodları"
            elif any(k in combined_meta for k in ["hesap", "chatgpt", "canva", "netflix", "spotify", "lisans"]):
                category = "Dijital Hesap, Lisans & Kupon Pazarı"

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

def run_coupon_scan():
    excluded = get_excluded_list()
    candidates = gather_candidates(excluded)
    
    print(f"\n[*] Birebir Kupon/Kod/Çek Hedef Grupları Canlı Doğrulanıyor ({len(candidates)} Aday)...")
    
    approved = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        future_to_uname = {executor.submit(check_coupon_group, uname): uname for uname in candidates}
        checked_count = 0
        
        for future in concurrent.futures.as_completed(future_to_uname):
            checked_count += 1
            res = future.result()
            if res:
                approved.append(res)
                print(f"[ONAYLANDI ✅ #{len(approved)}] @{res['username']:<25} | Üye: {res['members']:<6} (Online: {res['online']:<4}) | Kat: {res['category']}", flush=True)

    # Sort by online users, members, and relevance
    approved.sort(key=lambda x: (-x["online"], -x["members"], -x["relevance_score"]))
    
    print(f"\n=======================================================")
    print(f"🎉 TOPLAM DOĞRULANMIŞ BİREBİR KUPON/KOD GRUBU SAYISI: {len(approved)}")
    print(f"=======================================================\n")
    
    with open("birebir_saf_kupon_kod_gruplari.json", "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)

    with open("birebir_saf_kupon_kod_gruplari.txt", "w", encoding="utf-8") as f:
        for g in approved:
            f.write(f"{g['username']}\n")

    print("[*] Kaydedildi: 'birebir_saf_kupon_kod_gruplari.json' ve 'birebir_saf_kupon_kod_gruplari.txt'")

if __name__ == "__main__":
    run_coupon_scan()
