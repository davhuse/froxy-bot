import sys
import os

# Set standard output encoding to utf-8
sys.stdout.reconfigure(encoding='utf-8')

# Append root directory to path
sys.path.append(os.path.abspath("C:/Users/habil/.gemini/antigravity/scratch/tg-bot-reklam"))

import froxy_bot
import lisansarena_bot

print("=== KeyVadi Categories ===")
froxy_bot.load_products_from_file_or_scrape()
for k, v in froxy_bot.CATEGORIES.items():
    print(f"{k} ({v['title']}): {len(v['products'])} products")
    for pid, p in list(v['products'].items())[:3]:
        print(f"  - ID: {pid} | Title: {p['title']} | Price: {p['price']}")

print("\n=== LisansArena Categories ===")
lisansarena_bot.load_products_from_links_json()
for k, v in lisansarena_bot.CATEGORIES.items():
    print(f"{k} ({v['title']}): {len(v['products'])} products")
    for pid, p in list(v['products'].items())[:3]:
        print(f"  - ID: {pid} | Title: {p['title']} | Price: {p['price']}")
