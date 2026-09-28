import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
with open('jarvis_store_page.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find product cards
cards = re.findall(r'data-back-id="(\d+)".*?<h5[^>]*>([^<]+)</h5>.*?<span class="price-text[^"]*">([^<]+)</span>', html, re.DOTALL)
print(f"Found {len(cards)} products in jarvis_store_page.html:")
for pid, title, price in cards:
    print(f"ID: {pid} | Price: {price.strip()} | Title: {title.strip()}")

# Also find store URL or links
links = set(re.findall(r'https://www\.shopier\.com/[A-Za-z0-9_/-]+', html))
for l in sorted(links):
    if 'static' not in l and 'asset' not in l:
        print("Link:", l)
