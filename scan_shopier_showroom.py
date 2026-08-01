import urllib.request
import re
import json
import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

url = 'https://www.shopier.com/keyvadi'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

req = urllib.request.Request(url, headers=headers)

try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        print(f"HTML Fetched ({len(html)} bytes). Parsing...")

        soup = BeautifulSoup(html, 'html.parser')
        products = []

        # Find product items
        items = soup.find_all(class_=re.compile(r'product|item|card|box', re.I))
        for item in items:
            link_tag = item.find('a', href=True)
            title_tag = item.find(class_=re.compile(r'title|name|header', re.I)) or link_tag
            price_tag = item.find(class_=re.compile(r'price|cost|amount', re.I))

            if link_tag:
                href = link_tag['href']
                title = title_tag.get_text(strip=True) if title_tag else ''
                price = price_tag.get_text(strip=True) if price_tag else ''
                if title and ('shopier.com' in href or href.startswith('/') or re.search(r'\d+', href)):
                    products.append({'title': title, 'price': price, 'link': href})

        if not products:
            # Fallback regex search
            for m in re.finditer(r'href=["\']([^"\']*\d+)["\'][^>]*>([^<]+)', html):
                products.append({'title': m.group(2).strip(), 'link': m.group(1)})

        print(f"\nFOUND {len(products)} PRODUCTS ON SHOPIER KEYVADI:")
        for idx, p in enumerate(products):
            print(f"[{idx+1}] {p.get('title')} | Price: {p.get('price')} | Link: {p.get('link')}")

        with open('parsed_keyvadi_products.json', 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

except Exception as e:
    print(f"Scrape error: {e}")
