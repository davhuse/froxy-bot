import urllib.request
import urllib.parse
import re
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'
}

def test_sources():
    found_usernames = set()
    
    # 1. Telegramchannels.me
    keywords = ["kupon", "hesap", "lisans", "ticaret", "kod", "smm", "dijital", "pazar", "al sat", "indirim"]
    for kw in keywords:
        url = f"https://telegramchannels.me/tr/channels?search={urllib.parse.quote(kw)}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                for m in re.finditer(r"(?:t\.me/|@)([a-zA-Z0-9_]{4,32})", html):
                    u = m.group(1).lower()
                    if u not in {"joinchat", "share", "addstickers", "proxy", "bot", "channel", "telegram"}:
                        found_usernames.add(u)
                print(f"telegramchannels.me kw='{kw}' -> total unique: {len(found_usernames)}")
        except Exception as e:
            print(f"telegramchannels.me kw='{kw}' err: {e}")
            
    # 2. Bing search
    bing_queries = [
        'site:t.me "kupon satış"',
        'site:t.me "hesap satış" telegram',
        'site:t.me "lisans satış" telegram',
        'site:t.me "dijital pazar" telegram',
        'site:t.me "ticaret grubu" telegram',
        'site:t.me "kupon alım satım"',
        'site:t.me "kod alım satım"',
        'site:t.me "çek alım satım"'
    ]
    for bq in bing_queries:
        url = f"https://www.bing.com/search?q={urllib.parse.quote(bq)}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                for m in re.finditer(r"(?:t\.me/|telegram\.me/)([a-zA-Z0-9_]{4,32})", html):
                    u = m.group(1).lower()
                    if u not in {"joinchat", "share", "addstickers", "proxy", "bot", "channel", "telegram"}:
                        found_usernames.add(u)
                print(f"Bing bq='{bq}' -> total unique: {len(found_usernames)}")
        except Exception as e:
            print(f"Bing bq='{bq}' err: {e}")
            
    print(f"\nTOTAL FOUND: {len(found_usernames)}")
    print("Sample:", list(found_usernames)[:20])

if __name__ == "__main__":
    test_sources()
