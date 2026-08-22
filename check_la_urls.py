import json

with open('lisansarena_catalog.json', 'r', encoding='utf-8') as f:
    la = json.load(f)

print(f"Total in lisansarena_catalog.json: {len(la)}")
for p in la[:15]:
    print(f"[{p.get('id')}] {p.get('title')} -> url: {p.get('url')}")
