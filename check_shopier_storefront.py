import urllib.request, re

req = urllib.request.Request('https://www.shopier.com/lisansarena', headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')

# Find product cards or links
cards = re.findall(r'<a[^>]+href="([^"]*(?:/[0-9]+|ShowProductNew[^"]*))"[^>]*>(.*?)</a>', html, re.DOTALL)
print(f"Total links on /lisansarena: {len(cards)}")
for link, text in cards[:20]:
    clean_text = re.sub(r'\s+', ' ', text).strip()
    print(f"  {link} -> {clean_text[:60]}")
