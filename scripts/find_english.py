# -*- coding: utf-8 -*-
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 1. Inspect miniapp_dijitalpazarim/index.html
html = (ROOT / "miniapp_dijitalpazarim" / "index.html").read_text(encoding="utf-8")
print("--- MINIAPP HTML INSPECTION ---")
# Extract visible text outside <style> and <script>
clean_html = re.sub(r'<style.*?</style>', '', html, flags=re.DOTALL)
clean_html = re.sub(r'<script.*?</script>', '', clean_html, flags=re.DOTALL)
visible_texts = re.findall(r'>([^<]+)<', clean_html)
for t in visible_texts:
    t = t.strip()
    if t:
        print(f"Text: {t}")

# 2. Inspect miniapp_dijitalpazarim/products_db.json
print("\n--- PRODUCTS DB INSPECTION ---")
products = json.loads((ROOT / "miniapp_dijitalpazarim" / "products_db.json").read_text(encoding="utf-8"))
for p in products:
    print(f"Title: {p['title']} | Badge: {p.get('badge')} | Cat: {p.get('category')} | CatLabel: {p.get('category_label')}")
