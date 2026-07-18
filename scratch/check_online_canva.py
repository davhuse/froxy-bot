import urllib.request
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'Mozilla/5.0'}

def check_shop(name):
    url = f'https://www.shopier.com/{name}'
    print(f'Checking {url}...')
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            html = r.read().decode('utf-8', errors='ignore')
            print('  Length of HTML:', len(html))
            
            # Simple card parse
            # Cards might not use exact match but let's do a general search
            titles = re.findall(r'class="shopier-store--store-product-card-title">([^<]+)</h3>', html)
            links = re.findall(r'href="(https://www\.shopier\.com/[^/]+/\d+)"', html)
            print(f'  Found {len(titles)} titles, {len(links)} links')
            for t, l in zip(titles, links):
                if 'canva' in t.lower() or 'öğretmen' in t.lower() or 'ogretmen' in t.lower():
                    print(f'    Found: {t.strip()} -> {l}')
                    
            # Let's print all titles containing "canva" just to see
            for t in titles:
                if 'canva' in t.lower():
                    print('      Canva title:', t.strip())
    except Exception as e:
        print('  Error:', e)

check_shop('keyvadi')
check_shop('lisansarena')
