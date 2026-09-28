import json
import requests
from bs4 import BeautifulSoup
import sys

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

data = json.load(open('keyvadi_shopier_links.json', encoding='utf-8', errors='ignore'))
print(f"Checking KeyVadi ({len(data)} items)...")

wrong = []
for idx, it in enumerate(data):
    url = it.get('shopier_url') or it.get('url') or ''
    title = it.get('title') or ''
    if not url:
        continue
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            store_tag = soup.find('div', class_='follow-store-name') or soup.find('div', class_='store-title')
            sname = store_tag.get_text(strip=True) if store_tag else (soup.title.string if soup.title else 'Unknown')
            if 'keyvadi' not in sname.lower():
                print(f"[{idx+1}] WRONG: '{title}' ({url}) -> STORE: {sname}")
                wrong.append((title, url, sname))
        else:
            print(f"[{idx+1}] HTTP {r.status_code}: {title}")
    except Exception as e:
        print(f"[{idx+1}] Error {url}: {e}")

print(f"\nDone: {len(data) - len(wrong)}/{len(data)} OK, {len(wrong)} wrong stores found.")
