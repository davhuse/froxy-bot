import urllib.request
import ssl
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def scrape_shopier():
    print("Scraping Shopier showroom...")
    context = ssl._create_unverified_context()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    req = urllib.request.Request('https://www.shopier.com/keyvadi', headers=headers)
    
    try:
        with urllib.request.urlopen(req, context=context, timeout=15) as response:
            raw_data = response.read()
            # Try decoding with utf-8 first, fallback to windows-1254
            try:
                html = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                html = raw_data.decode('windows-1254', errors='ignore')
                
            # Regex to find product cards
            cards = html.split('class="product-card shopier--product-card')
            products = []
            
            for card in cards[1:]:
                # Extract link/ID
                link_match = re.search(r'href="(https://www\.shopier\.com/keyvadi/(\d+))"', card)
                title_match = re.search(r'class="shopier-store--store-product-card-title">([^<]+)</h3>', card)
                price_match = re.search(r'data-price="([^"]+)"', card)
                
                if link_match and title_match and price_match:
                    url = link_match.group(1)
                    pid = link_match.group(2)
                    title = title_match.group(1).strip()
                    price = price_match.group(1).strip()
                    
                    # Fix character encoding issues (e.g. if parsed with replacement characters)
                    # Let's clean up title & price
                    # If html was utf-8 but had raw ISO-8859-9 bytes, decode using correct charset:
                    # Let's check if the title has replacement chars or raw bytes
                    title = title.replace('\ufffd', 'ı') # quick fix for common Turkish char if decoded wrongly
                    # Wait, let's print and inspect
                    products.append({
                        "id": pid,
                        "title": title,
                        "price": price,
                        "url": url
                    })
            
            print(f"Scraped {len(products)} products successfully.")
            for p in products:
                print(f" - ID: {p['id']} | Title: {p['title']} | Price: {p['price']}")
                
            return products
    except Exception as e:
        print(f"Scraper error: {e}")
        return []

if __name__ == '__main__':
    scrape_shopier()
