import urllib.request
import re
from datetime import datetime, timezone

test_targets = ['me7alimsatim', 'kuponsat', 'ticaretZ', 'alimsatimmerkezii', 'ceksat', 'kinseimedyaticaret']
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

for u in test_targets:
    url = f'https://t.me/s/{u}'
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
            msgs = re.findall(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
            dates = re.findall(r'<time class="tgme_widget_message_date"[^>]*datetime="([^"]+)"', html)
            authors = re.findall(r'<a class="tgme_widget_message_owner_name"[^>]*>(.*?)</a>', html, re.DOTALL)
            if not authors:
                authors = re.findall(r'<div class="tgme_widget_message_from_author"[^>]*>(.*?)</div>', html, re.DOTALL)
                
            print(f'=== @{u} ===')
            print(f'HTML len: {len(html)}, Msgs: {len(msgs)}, Dates: {len(dates)}, Authors: {len(authors)}')
            if msgs:
                clean_first = re.sub(r'<[^>]+>', ' ', msgs[-1]).strip()
                print(f'Latest msg text: {clean_first[:100]} | Date: {dates[-1] if dates else "N/A"}')
    except Exception as e:
        print(f'=== @{u} ERROR: {e} ===')
