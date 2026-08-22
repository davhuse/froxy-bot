import json
from pathlib import Path

ROOT = Path('.')

for f in ["lisansarena_shopier_links.json", "lisansarena_catalog_additions.json"]:
    p = ROOT / f
    if p.exists():
        data = json.loads(p.read_text(encoding='utf-8'))
        print(f"=== {f} ({len(data)} items) ===")
        for item in data[:10]:
            print(f"[{item.get('id')}] {item.get('title')} -> url: {item.get('url') or item.get('link')}")
    else:
        print(f"=== {f} NOT FOUND ===")
