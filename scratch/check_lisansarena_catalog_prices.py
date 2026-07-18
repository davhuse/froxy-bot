import json
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

with open("lisansarena_shopier_links.json", "r", encoding="utf-8") as f:
    catalog = json.load(f)
    
print("LisansArena Catalog Products and Prices:")
for idx, p in enumerate(catalog):
    price_data = p.get("priceData", {})
    price = price_data.get("price", "0.00")
    print(f"{idx+1}: {p.get('title')} -> {price} TRY")
