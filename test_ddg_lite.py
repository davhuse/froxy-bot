import urllib.request
import urllib.parse
import re

def search_ddg_lite(query):
    url = "https://lite.duckduckgo.com/lite/"
    data = urllib.parse.urlencode({'q': query}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded'
    })
    usernames = set()
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_html = response.read().decode('utf-8', errors='ignore')
            html = urllib.parse.unquote(raw_html)
            for m in re.finditer(r"t\.me/(?:joinchat/|\+)?([A-Za-z0-9_]{4,32})", html):
                u = m.group(1).lower()
                if u not in {"joinchat", "share", "addstickers", "proxy", "iv", "s", "c", "bot", "channel", "login", "signup"}:
                    usernames.add(u)
    except Exception as e:
        print(f"Error for {query}: {e}")
    return usernames

if __name__ == "__main__":
    queries = [
        'site:t.me "kupon" "satış"',
        'site:t.me "çek sat" telegram',
        'site:t.me "hesap satış" telegram',
        'site:t.me "lisans satış" telegram',
        'site:t.me "smm" "ticaret" telegram'
    ]
    for q in queries:
        res = search_ddg_lite(q)
        print(f"{q} -> {len(res)} usernames found: {res}")
