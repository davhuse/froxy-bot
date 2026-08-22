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
# 1. LOAD MASTER BLACKLIST
# -------------------------------------------------------------
def get_master_blacklist():
    known = set()
    for fname in os.listdir("."):
        if not (fname.endswith(".json") or fname.endswith(".txt")):
            continue
        if fname in ["yeni_birebir_hedef_gruplar.json", "yeni_birebir_hedef_gruplar.txt"]:
            continue
        fpath = os.path.join(".", fname)
        try:
            if fname.endswith(".json"):
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, str):
                                u = item.strip().lower().lstrip("@")
                                if 3 < len(u) < 35:
                                    known.add(u)
                            elif isinstance(item, dict):
                                for k in ["username", "group", "id", "chat_id", "link"]:
                                    v = item.get(k)
                                    if v and isinstance(v, str):
                                        u = v.strip().lower().lstrip("@").replace("https://t.me/", "")
                                        if 3 < len(u) < 35:
                                            known.add(u)
                    elif isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(k, str) and 3 < len(k) < 35:
                                known.add(k.strip().lower().lstrip("@"))
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict):
                                        for subk in ["username", "group", "link"]:
                                            subv = item.get(subk)
                                            if subv and isinstance(subv, str):
                                                u = subv.strip().lower().lstrip("@").replace("https://t.me/", "")
                                                if 3 < len(u) < 35:
                                                    known.add(u)
                                    elif isinstance(item, str):
                                        u = item.strip().lower().lstrip("@")
                                        if 3 < len(u) < 35:
                                            known.add(u)
            elif fname.endswith(".txt"):
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        for m in re.finditer(r"(?:t\.me/|@|^|\s)([a-zA-Z0-9_]{4,32})", line):
                            u = m.group(1).lower()
                            if u not in {"joinchat", "share", "proxy", "http", "https", "true", "false", "none"}:
                                known.add(u)
        except Exception:
            pass
    return known

# -------------------------------------------------------------
# 2. GENERATE PERMUTATIONS & DIRECTORY CANDIDATES
# -------------------------------------------------------------
ROOTS = [
    # Kupon / Çek / Kod
    "kupon", "kuponlar", "kuponsatis", "kuponcu", "kuponpazari", "kuponborsasi", "kuponalimsatim",
    "kuponpaylasim", "kupondunyasi", "kuponmerkezi", "kuponplatformu", "kuponhane", "kuponkulubu",
    "cek", "ceksatis", "cekpazari", "cekalimsatim", "cektakas", "cekhakkinda", "hediyeceki", "marketceki",
    "kod", "kodsatis", "kodpazari", "kodalimsatim", "kodtakas", "kodmarketi", "kodmerkezi", "indirimkodu",
    "yemekkod", "promosyonkod", "kampanyakodu", "indirimceki", "indirimkuponu", "indirimler", "indirimkulubu",
    
    # Dijital Hesap / Lisans / Key
    "hesap", "hesapsatis", "hesappazari", "hesapalimsatim", "hesaptakas", "hesapmarketi", "hesapmerkezi",
    "dijitalhesap", "premiumhesap", "chatgptturkce", "chatgpthesap", "canvaprotr", "canvalisans",
    "netflixhesap", "spotifypremiumtr", "youtubepremiumtr", "adobehesap", "adobelisans",
    "lisans", "lisanssatis", "lisanspazari", "lisansmarket", "lisansmerkezi", "key", "keysatis",
    "keypazari", "windowskey", "officekey", "yazilimsatis", "yazilimticaret", "botpazari", "scriptsatis",
    
    # Pazar / Ticaret / SMM
    "dijitalpazar", "dijitalticaret", "dijitalmarket", "sanalticaret", "sanalpazar", "sanalmarket",
    "ticaretpazari", "alsatticaret", "ticaretgrubu", "ticarethanesi", "pazaryeritr", "letgotr", "ilanpazari",
    "serbestticaret", "turkiyticaret", "trticaret", "smmpazar", "smmticaret", "smmmarket", "sosyalmedyapazari",
    "takipcisatis", "hesapborsasi", "freelancetr", "webmastertr", "r10ticaret", "shopierticaret"
]

SUFFIXES = [
    "", "1", "2", "3", "01", "34", "tr", "_tr", "turkiye", "_turkiye", "grubu", "_grubu", "grup", "_grup",
    "official", "_official", "resmi", "merkez", "_merkez", "merkezi", "_merkezi", "pazar", "_pazar",
    "pazari", "_pazari", "market", "_market", "marketi", "_marketi", "borsa", "_borsa", "borsasi",
    "alimsatim", "_alimsatim", "alsat", "_alsat", "satis", "_satis", "ticaret", "_ticaret", "paylasim",
    "sohbet", "platformu", "kulubu", "dunyasi", "yeri", "_yeri", "merkezii", "satislari", "vip"
]

PREFIXES = [
    "", "tr_", "turk_", "turkiye_", "turk_", "saf_", "oto_", "mega_", "super_", "vip_", "net_", "pro_"
]

def build_candidate_pool(master_known):
    candidates = set()
    
    # 1. Permutations
    for r in ROOTS:
        for s in SUFFIXES:
            for p in PREFIXES:
                uname = f"{p}{r}{s}".strip("_").lower()
                if 4 <= len(uname) <= 32 and uname not in master_known:
                    candidates.add(uname)
                    
    print(f"[*] Üretilen Benzersiz Aday Sayısı: {len(candidates)}")
    return candidates

# -------------------------------------------------------------
# 3. STRICT RULES & FILTERS
# -------------------------------------------------------------
BETTING_TERMS = [
    "bahis", "casino", "slot", "sweet bonanza", "gates of olympus", "rulet",
    "blackjack", "iddaa", "tipster", "kupon tahmin", "maç tahmin", "oran şikesi",
    "bet", "deneme bonusu", "bonus veren", "pragmatic", "güvenilir bahis",
    "canlı bahis", "roll", "aviator", "zeplin", "canlibahis", "kripto sinyal", "forex"
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
    "pazar", "market", "al sat", "tedarik", "shopier", "hizmet", "takas"
]

def check_group_web(username):
    url = f"https://t.me/{username}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    })
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
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
            
            # Rule: MUST be a Group, NOT a channel, NOT a personal user
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
                
            # Rule: NOT dead -> Must have members >= 60 and online >= 3
            if members < 60 or online < 2:
                return None
                
            combined_meta = f"{title}\n{desc}".lower()
            
            # Rule: Negative filters
            if any(bt in combined_meta for bt in BETTING_TERMS):
                return None
            if any(st in combined_meta for st in SPAM_ILLEGAL_TERMS):
                return None
            if any(gt in combined_meta for gt in GAME_ACCOUNT_TERMS):
                return None
            if any(ad in combined_meta for ad in ADMIN_DEAL_TERMS):
                return None

            # Rule: Positive Target Relevance Score
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
                "about_description": desc[:150] if desc else "N/A",
                "t_me_link": f"https://t.me/{username}"
            }
    except Exception:
        return None

def run_deep_scan():
    master_known = get_master_blacklist()
    print(f"[*] Kara Listedeki / Bilinen Grup Sayısı: {len(master_known)}")
    
    candidates = list(build_candidate_pool(master_known))
    print(f"[*] Toplam Taranacak Aday Sayısı: {len(candidates)}")
    print(f"[*] Eşzamanlı Çoklu İş Parçacığı ile Canlı Doğrulama Başlatılıyor...\n")
    
    approved = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_uname = {executor.submit(check_group_web, uname): uname for uname in candidates}
        checked_count = 0
        
        for future in concurrent.futures.as_completed(future_to_uname):
            checked_count += 1
            res = future.result()
            if res:
                approved.append(res)
                print(f"[ONAYLANDI ✅ #{len(approved)}] @{res['username']} | {res['title'][:26]} | Üye: {res['members']} (Online: {res['online']}) | Kat: {res['category']}", flush=True)
                
            if checked_count % 500 == 0:
                print(f"  -> {checked_count}/{len(candidates)} aday tarandı... (Onaylanan: {len(approved)})", flush=True)

    approved.sort(key=lambda x: (-x["online"], -x["members"], -x["relevance_score"]))
    
    print(f"\n=======================================================")
    print(f"🎉 TARAMA BİTTİ: Toplam {len(approved)} Adet Birebir Hedef Grup Doğrulandı!")
    print(f"=======================================================\n")
    
    with open("yeni_birebir_hedef_gruplar.json", "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)

    with open("yeni_birebir_hedef_gruplar.txt", "w", encoding="utf-8") as f:
        for g in approved:
            f.write(f"{g['username']}\n")

    print("[*] Sonuçlar 'yeni_birebir_hedef_gruplar.json' ve 'yeni_birebir_hedef_gruplar.txt' dosyalarına kaydedildi.")

if __name__ == "__main__":
    run_deep_scan()
