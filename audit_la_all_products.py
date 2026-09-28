import json
import requests
from bs4 import BeautifulSoup
import sys

sys.stdout.reconfigure(encoding='utf-8')
data = json.load(open('miniapp_lisansarena/products_db.json', encoding='utf-8', errors='ignore'))
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

results = []
for idx, item in enumerate(data):
    url = item.get('shopier_url') or item.get('url') or ''
    title = item.get('title') or ''
    pid = item.get('id')
    entry = {'idx': idx, 'id': pid, 'title': title, 'url': url, 'is_lisansarena': False, 'store_name': ''}
    if not url or 'shopier.com' not in url:
        entry['store_name'] = 'No URL'
        results.append(entry)
        continue
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            store_tag = soup.find('div', class_='follow-store-name') or soup.find('div', class_='store-title')
            store_name = store_tag.get_text(strip=True) if store_tag else (soup.title.string if soup.title else 'Unknown')
            entry['store_name'] = store_name
            entry['is_lisansarena'] = 'lisansarena' in store_name.lower()
        else:
            entry['store_name'] = f'HTTP {r.status_code}'
    except Exception as e:
        entry['store_name'] = f'Error: {type(e).__name__}'
    results.append(entry)
    status_str = "OK" if entry['is_lisansarena'] else "FAKE/WRONG"
    print(f"[{idx+1}/{len(data)}] {status_str}: '{title[:25]}' ({url}) -> {entry['store_name']}")

# Summary
real_count = sum(1 for r in results if r['is_lisansarena'])
print(f"\nTotal: {len(results)} | Real LisansArena: {real_count} | Mismatched/External: {len(results) - real_count}")

with open('la_products_audit_result.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
