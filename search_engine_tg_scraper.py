import urllib.request
import urllib.parse
import re
import json
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def scrape_search_engines():
    found = set()
    
    queries = [
        # Turkish trade / coupon / code queries
        'site:t.me "alım satım" telegram',
        'site:t.me "alım-satım" telegram',
        'site:t.me "kupon" "satış" telegram',
        'site:t.me "kupon" "alım" telegram',
        'site:t.me "çek" "satış" telegram',
        'site:t.me "kod" "satış" telegram',
        'site:t.me "hesap satışı" telegram',
        'site:t.me "hesap alım satım" telegram',
        'site:t.me "lisans satışı" telegram',
        'site:t.me "key satışı" telegram',
        'site:t.me "dijital pazar" telegram',
        'site:t.me "dijital ticaret" telegram',
        'site:t.me "smm pazar" telegram',
        'site:t.me "smm ticaret" telegram',
        'site:t.me "ticaret grubu" telegram',
        'site:t.me "ticaret pazarı" telegram',
        'site:t.me "al sat grubu" telegram',
        'site:t.me "ilan pazarı" telegram',
        'site:t.me "yemeksepeti" "kupon" telegram',
        'site:t.me "trendyol" "indirim" telegram',
        'site:t.me "chatgpt" "hesap" telegram',
        'site:t.me "canva pro" telegram',
        'site:t.me "windows lisans" telegram',
        'site:t.me "sosyal medya pazarı" telegram'
    ]
    
    # Engines: DuckDuckGo HTML & Bing
    for q in queries:
        # DDG
        try:
            url_ddg = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(q)}"
            req = urllib.request.Request(url_ddg, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                for m in re.finditer(r"(?:t\.me/|telegram\.me/)([a-zA-Z0-9_]{4,32})", html):
                    u = m.group(1).lower()
                    if u not in {"joinchat", "share", "addstickers", "proxy", "bot", "channel", "telegram", "s", "c", "iv", "html"}:
                        found.add(u)
        except Exception:
            pass
            
        # Bing
        try:
            url_bing = f"https://www.bing.com/search?q={urllib.parse.quote(q)}"
            req = urllib.request.Request(url_bing, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                for m in re.finditer(r"(?:t\.me/|telegram\.me/)([a-zA-Z0-9_]{4,32})", html):
                    u = m.group(1).lower()
                    if u not in {"joinchat", "share", "addstickers", "proxy", "bot", "channel", "telegram", "s", "c", "iv", "html"}:
                        found.add(u)
        except Exception:
            pass
            
        time.sleep(0.3)
        
    print(f"Total scraped usernames from search engines: {len(found)}")
    with open("web_engine_found_groups.json", "w", encoding="utf-8") as f:
        json.dump(sorted(list(found)), f, indent=2)

if __name__ == "__main__":
    scrape_search_engines()
