import urllib.request

req = urllib.request.Request('https://www.shopier.com/lisansarena/51051024', headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')

idx = html.find('badge">T')
if idx != -1:
    print(html[idx-200:idx+250])
else:
    print("Not found")

# Also check for add to cart / buy button in the main form
import re
forms = re.findall(r'<form[^>]*>(.*?)</form>', html, re.DOTALL)
print(f"Forms found: {len(forms)}")
for f in forms:
    if 'button' in f.lower() or 'submit' in f.lower():
        print("Form button snippet:", f[:300])
