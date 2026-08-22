import urllib.request
import re
import html

test_groups = [
    "kuponkodalimsatimm", "kuponyaticaret", "wishx_2", "kodkuponmarketi", "ceksatkupon2",
    "Kuponcekm", "kuponceking", "satisrefim", "bedavainternetkralligigrubu", "kazandrio",
    "KodCek", "cek_kupon_kod_ilan", "mukyemek", "kodmalf", "uygunkod", "kodpazari",
    "KodKuponMerkezi", "kuponkodmerkez", "herkesibeklerimm", "Minakuponkodsatis"
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for u in test_groups:
    url = f"https://t.me/{u}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            content_clean = html.unescape(content)
            
            title = re.search(r'<div class="tgme_page_title"[^>]*><span[^>]*>(.*?)</span>', content_clean, re.DOTALL)
            extra = re.search(r'<div class="tgme_page_extra"[^>]*>(.*?)</div>', content_clean, re.DOTALL)
            desc = re.search(r'<div class="tgme_page_description"[^>]*>(.*?)</div>', content_clean, re.DOTALL)
            
            t_str = title.group(1).strip() if title else "NO TITLE"
            e_str = extra.group(1).strip() if extra else "NO EXTRA"
            d_str = desc.group(1).strip() if desc else "NO DESC"
            
            print(f"@{u:<22} | Title: {t_str[:25]:<25} | Extra: {e_str:<25}")
    except Exception as e:
        print(f"@{u:<22} | ERR: {e}")
