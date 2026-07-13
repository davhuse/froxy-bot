import json
import os
import re

def main():
    if not os.path.exists("created_shopier_products.json"):
        print("created_shopier_products.json not found! Run create_shopier_products_api.py first.")
        return
        
    with open("created_shopier_products.json", "r", encoding="utf-8") as f:
        new_products = json.load(f)
        
    print(f"Loaded {len(new_products)} new products to integrate.")
    
    # 1. Update parsed_keyvadi_products.json
    kv_file = "parsed_keyvadi_products.json"
    if os.path.exists(kv_file):
        with open(kv_file, "r", encoding="utf-8") as f:
            kv_products = json.load(f)
    else:
        kv_products = []
        
    existing_ids = {p["id"] for p in kv_products}
    added_count = 0
    for np in new_products:
        if np["id"] not in existing_ids:
            kv_products.append({
                "id": np["id"],
                "title": np["title"],
                "price": np["price"] + " TL" if not np["price"].endswith("TL") else np["price"],
                "url": np["url"]
            })
            added_count += 1
            
    with open(kv_file, "w", encoding="utf-8") as f:
        json.dump(kv_products, f, indent=2, ensure_ascii=False)
    print(f"Added {added_count} products to {kv_file} (Total: {len(kv_products)}).")
    
    # 2. Update bot_config.json (shopier_links)
    config_file = "bot_config.json"
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        links = config.setdefault("shopier_links", {})
        for np in new_products:
            links[np["slug"]] = np["url"]
            
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print("Updated shopier_links in bot_config.json.")
        
    # 3. Update froxy_bot.py (INJECTED_PRODUCTS and Category Keywords)
    bot_file = "froxy_bot.py"
    if os.path.exists(bot_file):
        with open(bot_file, "r", encoding="utf-8") as f:
            bot_content = f.read()
            
        # Find INJECTED_PRODUCTS block
        match = re.search(r'INJECTED_PRODUCTS\s*=\s*\[(.*?)\]', bot_content, re.DOTALL)
        if match:
            injected_str = match.group(1)
            # Build list of existing items
            # Parse dict items manually since it's a python list representation
            new_injections = []
            for np in new_products:
                item_str = f'    {{"id": "{np["id"]}", "title": "{np["title"]}", "price": "{np["price"]}", "url": "{np["url"]}"}}'
                if np["id"] not in injected_str:
                    new_injections.append(item_str)
            
            if new_injections:
                updated_injected_str = injected_str.strip() + ",\n" + ",\n".join(new_injections) + "\n"
                bot_content = bot_content.replace(injected_str, updated_injected_str)
                print(f"Injected {len(new_injections)} products into INJECTED_PRODUCTS in froxy_bot.py.")
                
        # Update keywords for 'ai' category to include 'perplexity'
        bot_content = bot_content.replace(
            '"gemini", "grok", "ai", "gamma", "kiro", "chatgpt", "openai", "copilot", "claude", "midjourney", "semrush", "deepl", "quill", "ideogram", "envato", "freepik"',
            '"gemini", "grok", "ai", "gamma", "kiro", "chatgpt", "openai", "copilot", "claude", "midjourney", "semrush", "deepl", "quill", "ideogram", "envato", "freepik", "perplexity", "magnific"'
        )
        
        # Update keywords for 'design' category to include 'crunchyroll', 'hbo'
        bot_content = bot_content.replace(
            '"canva", "adobe", "creative cloud", "express", "capcut", "duolingo", "scribd", "design", "tasarım", "spotify", "netflix", "windows", "win ", "win10", "win11", "office", "key", "lisans", "autodesk", "figma", "wordpress", "grammarly", "vpn", "antivirüs", "antivirus", "xbox", "steam", "game pass"',
            '"canva", "adobe", "creative cloud", "express", "capcut", "duolingo", "scribd", "design", "tasarım", "spotify", "netflix", "windows", "win ", "win10", "win11", "office", "key", "lisans", "autodesk", "figma", "wordpress", "grammarly", "vpn", "antivirüs", "antivirus", "xbox", "steam", "game pass", "crunchyroll", "hbo", "prime video"'
        )
        
        with open(bot_file, "w", encoding="utf-8") as f:
            f.write(bot_content)
        print("Updated froxy_bot.py keywords and injections.")

if __name__ == "__main__":
    main()
