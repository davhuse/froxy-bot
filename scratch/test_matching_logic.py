import json
import os
import sys

# Set path to import from parent directory
sys.path.append(r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam")
from otomatik_katil import match_product_from_text

# Load the generated keyvadi links
links_path = r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\keyvadi_shopier_links.json"

if not os.path.exists(links_path):
    print("Error: keyvadi_shopier_links.json not found!")
    sys.exit(1)

with open(links_path, "r", encoding="utf-8") as f:
    products = json.load(f)

print(f"Loaded {len(products)} products for KeyVadi.")

# Test queries
test_queries = [
    "hbo",
    "hbo max var mı?",
    "netflix",
    "netflix 4k fiyatı nedir?",
    "canva",
    "canva pro link alabilir miyim?",
    "prime video",
    "perplexity pro",
    "grok",
    "super grok 3 aylık",
    "deepl",
    "deepl ortak",
    "telegram hesabı",
    "office 365",
    "windows 10"
]

print("\n=== RUNNING KEYWORD MATCHING TEST ===")
for query in test_queries:
    matched, score = match_product_from_text(query, products)
    if matched:
        print(f"Query: '{query}' -> MATCHED: '{matched['title']}' (Score: {score}) -> Link: {matched['url']}")
    else:
        print(f"Query: '{query}' -> [NO MATCH]")

print("\nTest complete!")
