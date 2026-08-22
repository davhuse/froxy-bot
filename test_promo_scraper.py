import urllib.request
import re
from bs4 import BeautifulSoup

def get_usernames_from_tg_channel(channel):
    url = f"https://t.me/s/{channel}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    })
    found = set()
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            html = r.read().decode('utf-8', errors='ignore')
            for m in re.finditer(r"t\.me/(?:joinchat/|\+)?([A-Za-z0-9_]{4,32})", html):
                u = m.group(1).lower()
                if u not in {"joinchat", "share", "addstickers", "proxy", "iv", "s", "c", "bot", "channel", channel.lower()}:
                    found.add(u)
    except Exception as e:
        print(f"Error on {channel}: {e}")
    return found

if __name__ == "__main__":
    promo_channels = [
        "turkiyegruplari", "grupvekanallar", "turkiyegrupvekanallar", "turkiyetanitim",
        "gruplarvekanallar", "reklamkanali", "turkiyereklam", "gruptanitimi",
        "reklamlar", "kanaltanitim", "telegramturkiye", "turkiyeduyuru"
    ]
    all_found = set()
    for ch in promo_channels:
        res = get_usernames_from_tg_channel(ch)
        print(f"Channel @{ch} -> {len(res)} usernames found")
        all_found.update(res)
    print(f"\nTotal unique usernames scraped: {len(all_found)}")
