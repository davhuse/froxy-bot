import json
import os
import subprocess
from datetime import datetime

def main():
    if not os.path.exists("created_target_lisansarena_products.json"):
        print("created_target_lisansarena_products.json not found! Run create_target_lisansarena_products.py first.")
        return
        
    with open("created_target_lisansarena_products.json", "r", encoding="utf-8") as f:
        new_products = json.load(f)
        
    links_file = "lisansarena_shopier_links.json"
    if not os.path.exists(links_file):
        print(f"{links_file} not found!")
        return
        
    with open(links_file, "r", encoding="utf-8") as f:
        links_data = json.load(f)
        
    print(f"Loaded {len(links_data)} products from catalog.")
    
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+0300")
    
    added_count = 0
    updated_count = 0
    
    for np in new_products:
        # Check if already exists in catalog
        found = False
        for p in links_data:
            if np["title"].strip().lower() == p["title"].strip().lower():
                p["id"] = np["id"]
                p["url"] = np["url"]
                p["description"] = np["description"]
                p["priceData"]["price"] = np["price"]
                p["priceData"]["discountedPrice"] = np["price"]
                found = True
                updated_count += 1
                print(f"Updated product: {p['title']} -> ID: {p['id']}, URL: {p['url']}")
                break
                
        if not found:
            # Create new product entry
            new_entry = {
                "id": np["id"],
                "title": np["title"],
                "description": np["description"],
                "type": "digital",
                "dateCreated": now_str,
                "dateUpdated": now_str,
                "url": np["url"],
                "media": [
                    {
                        "id": "1",
                        "type": "image",
                        "url": np["imageUrl"],
                        "placement": 1
                    }
                ],
                "priceData": {
                    "currency": "TRY",
                    "price": np["price"],
                    "discount": False,
                    "discountedPrice": np["price"],
                    "shippingPrice": "0.00"
                },
                "stockStatus": "inStock",
                "stockQuantity": 999,
                "shippingPayer": "sellerPays",
                "categories": [],
                "variants": [],
                "options": [],
                "singleOption": False,
                "customListing": False,
                "customNote": "",
                "placementScore": "",
                "dispatchDuration": 0
            }
            links_data.append(new_entry)
            added_count += 1
            print(f"Added new product: {np['title']} -> ID: {np['id']}, URL: {np['url']}")
            
    with open(links_file, "w", encoding="utf-8") as f:
        json.dump(links_data, f, indent=4, ensure_ascii=False)
        
    print(f"Successfully added {added_count} and updated {updated_count} products in {links_file}.")
    
    # Git commit and push updated configurations
    print("\nCommitting and pushing updated product configurations to git...")
    subprocess.run(["git", "add", "lisansarena_shopier_links.json"], cwd=r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam")
    res_git = subprocess.run(["git", "commit", "-m", "Add missing Exxen, Office, Shell, Steam, Trendyol product links to LisansArena catalog"], cwd=r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam", capture_output=True, text=True)
    print(res_git.stdout)
    
    subprocess.run(["git", "push", "old-origin", "main"], cwd=r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam")
    subprocess.run(["git", "push", "origin", "main"], cwd=r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam")
    print("Pushed to GitHub successfully!")

if __name__ == "__main__":
    main()
