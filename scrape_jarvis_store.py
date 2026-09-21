import urllib.request
import re
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

req = urllib.request.Request(
    'https://www.shopier.com/JarvisStore',
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
)

try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        print(f"Store loaded! Length: {len(html)}")
        with open("jarvis_store_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        # Regex search for products in Shopier HTML
        matches = re.findall(r'<a\s+href="([^"]+)"[^>]*>([\s\S]*?)</a>', html)
        for href, content in matches:
            if 'ShowProductNew' in href or re.search(r'/\d+$', href):
                title_match = re.search(r'class="[^"]*product-title[^"]*"[^>]*>([^<]+)', content)
                price_match = re.search(r'class="[^"]*price[^"]*"[^>]*>([^<]+)', content)
                title = title_match.group(1).strip() if title_match else re.sub(r'<[^>]+>', '', content).strip()
                price = price_match.group(1).strip() if price_match else ""
                print(f"Product: {title} | Price: {price} | URL: {href}")
except Exception as e:
    print(f"Error: {e}")
