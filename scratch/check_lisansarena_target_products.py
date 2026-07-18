import json

with open("lisansarena_shopier_links.json", "r", encoding="utf-8") as f:
    products = json.load(f)

print("Checking products in LisansArena catalog matching user request:")
target_keywords = ["youtube", "exxen", "spotify", "trendyol", "shell", "steam", "office"]
for p in products:
    title = p["title"].lower()
    for kw in target_keywords:
        if kw in title:
            # Check if id starts with '279183' or has mock url
            is_mock = "keyvadi" in p["url"] or p["id"].startswith("279183")
            print(f"- Title: {p['title']}")
            print(f"  ID: {p['id']} | URL: {p['url']}")
            print(f"  Status: {'MOCK/MISSING REAL LINK' if is_mock else 'REAL'}")
            print("-" * 40)
            break
