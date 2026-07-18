import json
import os
import subprocess

def main():
    if not os.path.exists("created_lisansarena_products.json"):
        print("created_lisansarena_products.json not found! Run create_lisansarena_products.py first.")
        return
        
    with open("created_lisansarena_products.json", "r", encoding="utf-8") as f:
        new_products = json.load(f)
        
    links_file = "lisansarena_shopier_links.json"
    if not os.path.exists(links_file):
        print(f"{links_file} not found!")
        return
        
    with open(links_file, "r", encoding="utf-8") as f:
        links_data = json.load(f)
        
    updated_count = 0
    for np in new_products:
        found = False
        for p in links_data:
            # Let's match case-insensitively or by cleaning spaces
            t1 = p["title"].strip().lower().replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ö", "o").replace("ü", "u").replace("ç", "c")
            t2 = np["title"].strip().lower().replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ö", "o").replace("ü", "u").replace("ç", "c")
            if t1 == t2 or np["title"].strip().lower() == p["title"].strip().lower():
                p["id"] = np["id"]
                p["url"] = np["url"]
                found = True
                updated_count += 1
                print(f"Updated product: {p['title']} -> ID: {p['id']}, URL: {p['url']}")
                break
        if not found:
            print(f"Warning: Product not found in links json: {np['title']}")
            
    with open(links_file, "w", encoding="utf-8") as f:
        json.dump(links_data, f, indent=4, ensure_ascii=False)
        
    print(f"Successfully updated {updated_count} products in {links_file}.")
    
    # Git commit and push updated configurations
    print("\nCommitting and pushing updated product configurations to git...")
    subprocess.run(["git", "add", "lisansarena_shopier_links.json"], cwd=r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam")
    res_git = subprocess.run(["git", "commit", "-m", "Integrate 11 new real product Shopier links into LisansArena catalog"], cwd=r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam", capture_output=True, text=True)
    print(res_git.stdout)
    
    subprocess.run(["git", "push", "old-origin", "main"], cwd=r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam")
    subprocess.run(["git", "push", "origin", "main"], cwd=r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam")
    print("Pushed to GitHub successfully!")

if __name__ == "__main__":
    main()
