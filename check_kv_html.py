import urllib.request, re, json

url = 'https://www.shopier.com/keyvadi'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

# Check if there are product links or JSON objects embedded in the page
print("Page length:", len(html))
# Find all links like /keyvadi/... or /...
links = re.findall(r'https://www\.shopier\.com/(\d+)', html)
print("Found numeric product links:", len(links), links[:10])
# Check for "bakiye"
bakiye_matches = re.findall(r'.{0,50}bakiye.{0,50}', html, re.IGNORECASE)
print("Bakiye matches in HTML:", len(bakiye_matches))
for b in bakiye_matches[:10]:
    print("   ->", b.strip())
