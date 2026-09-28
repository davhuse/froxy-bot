import urllib.request, json, re

with open('lisansarena_topup_products.json') as f:
    pkgs = json.load(f)

for amt, pid in pkgs.items():
    u = f'https://www.shopier.com/lisansarena/{pid}'
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
        tukendi = 'Tükendi' in html
        title_m = re.search(r'<title>(.*?)</title>', html)
        title = title_m.group(1) if title_m else 'No title'
        print(f'{amt} TL (PID: {pid}) -> Tükendi: {tukendi} | Title: {title}')
    except Exception as e:
        print(f'{amt} TL (PID: {pid}) -> ERROR: {e}')
