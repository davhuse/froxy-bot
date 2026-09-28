import urllib.request, re

req = urllib.request.Request('https://www.shopier.com/lisansarena', headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')

# Check how cards are rendered:
cards = re.findall(r'<div class="product-card\b[^"]*">(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
print("Found cards:", len(cards))
# Or search for 'Tükendi' inside cards:
print("Tükendi count on main page:", html.count("Tükendi"))
print("Is shop suspended or closed?")
if "kapalı" in html.lower() or "tatil" in html.lower() or "bakım" in html.lower():
    print("Store might be in vacation/maintenance mode!")

# Let's inspect the actual HTML of one product card:
matches = re.findall(r'<a[^>]+href="https://www.shopier.com/lisansarena/(\d+)"[^>]*>.*?</a>', html, re.DOTALL)
print(f"Product IDs found: {len(matches)}")
for pid in matches[:5]:
    # Fetch that product page and see full text
    req_p = urllib.request.Request(f'https://www.shopier.com/lisansarena/{pid}', headers={'User-Agent': 'Mozilla/5.0'})
    html_p = urllib.request.urlopen(req_p).read().decode('utf-8', errors='ignore')
    has_buy_button = 'satın al' in html_p.lower() or 'sepete ekle' in html_p.lower()
    has_tukendi = 'tükendi' in html_p.lower()
    print(f"  PID {pid}: buy_btn={has_buy_button}, tukendi={has_tukendi}")
