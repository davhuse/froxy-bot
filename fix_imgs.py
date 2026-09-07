import json, urllib.request, re

with open('miniapp_froxy/products_db.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

for p in products:
    url = p.get('url')
    if not url: continue
    
    # Check if url has an ID
    if '/froxyai/' in url:
        # Shopier might return 404 for invalid froxyai/ endpoints, let's change them to KeyVadi or skip
        pass

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            m = re.search(r'<meta\s+property=[\'"]og:image[\'"]\s+content=[\'"]([^\'"]+)[\'"]', html)
            if m:
                p['image'] = m.group(1)
                print(p['title'], '->', p['image'])
    except Exception as e:
        print('Error on', p['title'], e)

with open('miniapp_froxy/products_db.json', 'w', encoding='utf-8') as f:
    json.dump(products, f, ensure_ascii=False, indent=2)
