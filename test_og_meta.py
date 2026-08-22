import urllib.request
import re
import html
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

test_groups = [
    "kuponceking", "satisrefim", "bedavainternetkralligigrubu", "kazandrio",
    "KodCek", "cek_kupon_kod_ilan", "mukyemek", "kodmalf", "uygunkod", "kodpazari",
    "KodKuponMerkezi", "kuponkodmerkez", "herkesibeklerimm", "Minakuponkodsatis",
    "letgoilanlari", "alimsatimmerkezii", "ticaretyapn", "yucekuponsatis", "ceksatkupon"
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for u in test_groups:
    url = f"https://t.me/{u}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            content_clean = html.unescape(content)
            
            og_title = re.search(r'<meta property="og:title" content="([^"]+)"', content_clean)
            extra = re.search(r'<div class="tgme_page_extra"[^>]*>(.*?)</div>', content_clean, re.DOTALL)
            og_desc = re.search(r'<meta property="og:description" content="([^"]+)"', content_clean)
            
            t_str = og_title.group(1).strip() if og_title else "NO TITLE"
            e_str = extra.group(1).strip() if extra else "NO EXTRA"
            d_str = og_desc.group(1).strip() if og_desc else "NO DESC"
            
            print(f"@{u:<22} | Title: {t_str[:25]:<25} | Extra: {e_str:<25} | Desc: {d_str[:35]}")
    except Exception as e:
        print(f"@{u:<22} | ERR: {e}")
