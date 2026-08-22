import json
import os
import re
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
import time

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

# -------------------------------------------------------------
# 1. EXHAUSTIVE BLACKLIST / KNOWN DATABASE
# -------------------------------------------------------------
def compile_master_blacklist():
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

    print(f"[*] Toplam Bilinen / Kara Listedeki Grup Sayısı: {len(known)}", flush=True)
    return known

# -------------------------------------------------------------
# 2. STRICT FILTERS & CATEGORIES
# -------------------------------------------------------------
BETTING_TERMS = [
    "bahis", "casino", "slot", "sweet bonanza", "gates of olympus", "rulet",
    "blackjack", "iddaa", "tipster", "kupon tahmin", "maç tahmin", "oran şikesi",
    "bet", "deneme bonusu", "bonus veren", "pragmatic", "güvenilir bahis",
    "canlı bahis", "roll", "aviator", "zeplin", "canlibahis", "kripto sinyal"
]

SPAM_ILLEGAL_TERMS = [
    "cc mail", "carding", "warez", "crack", "nulled", "escort", "porno", "lezbiyen",
    "gay", "ifsa", "ifşa", "tr ifsa", "yetiskin", "18+", "+18", "vip grup", "link tl",
    "illegal", "paneli patlat", "datacı", "muris", "gsm tc", "cc alım"
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
    "indirim haberleri", "günün fırsatları"
]

POSITIVE_TERMS = [
    "kupon", "çek", "cek", "kod", "indirim", "yemeksepeti", "trendyol", "getir", "migros",
    "hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "gemini", "claude",
    "lisans", "key", "windows", "office", "antivirüs", "vpn", "smm", "panel",
    "takipçi", "sosyal medya", "dijital", "ticaret", "alım", "satım", "satış", "satis",
    "fiyat", "tl", "₺", "stok", "dm", "özelden", "teslim", "güvenli", "aracı", "ilan", "devir",
    "pazar", "market", "al sat", "tedarik", "shopier", "hizmet"
]

# -------------------------------------------------------------
# 3. HTTP TELEGRAM WEB SCRAPER & INSPECTOR (ZERO API RATE LIMIT)
# -------------------------------------------------------------
def inspect_telegram_web(username):
    url = f"https://t.me/{username}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    })
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
            # Check if page exists
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
            
            # Clean HTML tags
            title = re.sub(r'<[^>]+>', '', title).strip()
            desc = re.sub(r'<[^>]+>', ' ', desc).strip()
            
            # Check if it's a channel (subscribers) or group (members)
            is_channel = "subscribers" in extra.lower() or "abone" in extra.lower()
            is_group = "members" in extra.lower() or "üye" in extra.lower() or "online" in extra.lower()
            
            # Parse members & online
            mem_m = re.search(r'([0-9\s]+)\s*(?:members|üye|subscribers|abone)', extra, re.IGNORECASE)
            members = 0
            if mem_m:
                members = int(re.sub(r'\s+', '', mem_m.group(1)))
                
            online_m = re.search(r'([0-9\s]+)\s*online', extra, re.IGNORECASE)
            online = 0
            if online_m:
                online = int(re.sub(r'\s+', '', online_m.group(1)))
                
            return {
                "username": username,
                "title": title,
                "extra": extra,
                "desc": desc,
                "members": members,
                "online": online,
                "is_channel": is_channel,
                "is_group": is_group
            }
    except Exception:
        return None

# Search web directories for keywords
def harvest_web_candidates():
    candidates = set()
    queries = [
        'site:t.me "kupon satış" telegram',
        'site:t.me "kupon alım satım" telegram',
        'site:t.me "çek satış" telegram',
        'site:t.me "kod satış" telegram',
        'site:t.me "hesap alım satım" telegram',
        'site:t.me "hesap satış" telegram',
        'site:t.me "lisans satış" telegram',
        'site:t.me "dijital pazar" telegram',
        'site:t.me "smm pazar" telegram',
        'site:t.me "ticaret grubu" telegram',
        'site:t.me "al sat grubu" telegram',
        'site:t.me "yemeksepeti kupon" telegram',
        'site:t.me "trendyol indirim kodu" telegram',
        'site:t.me "chatgpt plus satış" telegram',
        'site:t.me "canva pro lisans" telegram',
        'site:t.me "windows key lisans" telegram'
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    
    print("[*] DuckDuckGo & Web Dizinlerinden Adaylar Taranıyor...", flush=True)
    for q in queries:
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(q)}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                for m in re.finditer(r"(?:t\.me/|telegram\.me/)([a-zA-Z0-9_]{4,32})", html):
                    u = m.group(1).lower()
                    if u not in {"joinchat", "share", "addstickers", "proxy", "html", "bot", "telegram", "channel", "s", "c", "iv"}:
                        candidates.add(u)
            time.sleep(0.5)
        except Exception:
            pass
            
    print(f"[*] Web aramasından toplanan ham aday sayısı: {len(candidates)}", flush=True)
    return candidates

if __name__ == "__main__":
    cands = harvest_web_candidates()
    print(f"Toplam: {len(cands)}")
    for u in list(cands)[:10]:
        info = inspect_telegram_web(u)
        print(info)
