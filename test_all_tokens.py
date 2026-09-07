import os
import re
import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

seen_tokens = set()
for root, dirs, files in os.walk('.'):
    if '.git' in root or 'venv' in root or 'output' in root: continue
    for f in files:
        if f.endswith('.py') or f.endswith('.json') or f.endswith('.txt') or f.endswith('.env'):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
                    text = handle.read()
                    matches = re.findall(r'eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}', text)
                    for t in matches:
                        seen_tokens.add(t)
            except Exception: pass

print(f"Found {len(seen_tokens)} distinct tokens. Testing them against Shopier API...")

for token in seen_tokens:
    req = urllib.request.Request('https://api.shopier.com/v1/products?limit=1', headers={
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    })
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
            products = json.loads(resp.read().decode('utf-8'))
            if products and len(products) > 0:
                p = products[0]
                url = p.get('url', '')
                title = p.get('title', '')
                print(f"✅ WORKING TOKEN! First product: {title} | URL: {url} | Token: {token[:15]}...{token[-10:]}")
            else:
                print(f"✅ WORKING TOKEN (Empty store)! Token: {token[:15]}...{token[-10:]}")
    except Exception as e:
        # print("Failed:", e)
        pass
