import urllib.request, json, ssl, os, re, sys

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with open('restore_all_env.py', 'r', encoding='utf-8') as f:
    text = f.read()

token = re.search(r'"SHOPIER_KEYVADI_ACCESS_TOKEN":\s*"([^"]+)"', text).group(1)

with open('keyvadi_shopier_links.json', 'r', encoding='utf-8') as f:
    links = json.load(f)

bakiye_items = [item for item in links if 'bakiye' in item.get('title', '').lower()]
print(f"Found {len(bakiye_items)} bakiye listings in keyvadi_shopier_links.json:")

deleted_count = 0
for b in bakiye_items:
    pid = str(b.get('id'))
    title = b.get('title')
    print(f"\nDeleting Shopier Listing ID: {pid} ({title})...")
    del_req = urllib.request.Request(f"https://api.shopier.com/v1/products/{pid}", headers={
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }, method="DELETE")
    try:
        with urllib.request.urlopen(del_req, context=ctx) as r:
            code = r.getcode()
            print(f"   -> Shopier DELETE response: HTTP {code}")
            deleted_count += 1
    except urllib.error.HTTPError as e:
        print(f"   -> Shopier DELETE HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"   -> Error: {e}")

# Now clean keyvadi_shopier_links.json by removing all bakiye items
clean_links = [item for item in links if 'bakiye' not in item.get('title', '').lower()]
with open('keyvadi_shopier_links.json', 'w', encoding='utf-8') as f:
    json.dump(clean_links, f, ensure_ascii=False, indent=2)

print(f"\nCleaned keyvadi_shopier_links.json: went from {len(links)} to {len(clean_links)} items.")
