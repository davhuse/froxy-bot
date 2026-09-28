import json
import requests
from bs4 import BeautifulSoup
import sys

sys.stdout.reconfigure(encoding='utf-8')
data = json.load(open('miniapp_lisansarena/products_db.json', encoding='utf-8', errors='ignore'))
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

print(f"Checking store names for products in miniapp_lisansarena/products_db.json...")
checked = 0
for item in data:
    url = item.get('shopier_url') or item.get('url') or ''
    title = item.get('title') or ''
    if not url or 'shopier.com' not in url:
        continue
    try:
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            # Extract store name
            store_tag = soup.find('div', class_='follow-store-name') or soup.find('div', class_='store-title')
            store_name = store_tag.get_text(strip=True) if store_tag else (soup.title.string if soup.title else 'Unknown')
            if 'lisansarena' not in store_name.lower():
                print(f"MISMATCH! Product: '{title}' ({url}) -> STORE: '{store_name}'")
            else:
                print(f"MATCH: '{title[:30]}' -> {store_name}")
        else:
            print(f"HTTP {r.status_code} for '{title}' ({url})")
    except Exception as e:
        print(f"Error {url}: {e}")
    checked += 1
    if checked >= 20:
        break
