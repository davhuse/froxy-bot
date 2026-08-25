import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

url = "https://froxy-bot-live-r5se.onrender.com/la/app/api/products"
res = urllib.request.urlopen(url)
data = json.loads(res.read().decode("utf-8"))

if isinstance(data, dict):
    products = data.get("products", [])
else:
    products = data

print(f"Total LIVE Products: {len(products)}")
for p in products:
    title = p.get("title")
    price = p.get("price")
    cat = p.get("category")
    img = p.get("image")
    print(f"  ✓ {title:45s} | {price:>10s} | {cat:10s} | {img}")

# Also verify an image loads from server
img_test_url = f"https://froxy-bot-live-r5se.onrender.com/la/app/{products[0]['image']}"
img_res = urllib.request.urlopen(img_test_url)
print(f"\nImage test URL: {img_test_url} -> Status Code: {img_res.getcode()} (Bytes: {len(img_res.read())})")
