import json
import requests
from bs4 import BeautifulSoup
import sys

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for catalog_name, fpath, brand_keyword in [
    ('Froxy', 'froxy_shopier_links.json', 'froxy'),
    ('Jarvis', 'jarvis_shopier_products.json', 'jarvis'),
]:
    data = json.load(open(fpath, encoding='utf-8', errors='ignore'))
    print(f"\n=== Checking {catalog_name} ({len(data)} items) ===")
    for it in data:
        url = it.get('shopier_url') or it.get('url') or ''
        title = it.get('title') or ''
        if not url:
            print(f"NO URL: {title}")
            continue
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                store_tag = soup.find('div', class_='follow-store-name') or soup.find('div', class_='store-title')
                sname = store_tag.get_text(strip=True) if store_tag else (soup.title.string if soup.title else 'Unknown')
                print(f"'{title[:25]}' ({url}) -> STORE: {sname}")
            else:
                print(f"HTTP {r.status_code}: {title} ({url})")
        except Exception as e:
            print(f"Error {url}: {e}")
