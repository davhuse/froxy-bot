import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Mock class to simulate Telethon events
class MockSender:
    def __init__(self, sender_id, username, first_name):
        self.id = sender_id
        self.username = username
        self.first_name = first_name
        self.bot = False

class MockEvent:
    def __init__(self, sender_id, text, username="testuser", first_name="Test"):
        self.sender_id = sender_id
        self.raw_text = text
        self.is_private = True
        self.out = False
        self.replied_text = None
        self.sender = MockSender(sender_id, username, first_name)
        
    async def get_sender(self):
        return self.sender
        
    async def reply(self, text):
        self.replied_text = text
        print(f"  [REPLY SENT] ->\n{text}")

# Import the auto-reply handler logic from otomatik_katil
sys.path.append(os.path.abspath("."))
import otomatik_katil

# Define test cases
test_cases = [
    # (Client Name, Message Text, Expected Store)
    ("Hesap #1", "spotify ve youtube premium var mı?", "KeyVadi"),
    ("Hesap #2", "canva pro öğretmen", "KeyVadi"),
    ("Hesap #3", "netflix ultra 4k ve canva pro", "LisansArena"),
    ("Hesap #3", "gemini pro 12 aylık", "LisansArena")
]

async def run_simulation():
    print("=== Auto-Reply Simulation Test ===")
    
    # We mock our_user_ids to exclude our test sender (sender_id = 999999)
    our_user_ids = {8823916561, 8816312669}
    
    for client_name, msg_text, expected_store in test_cases:
        print(f"\n--- Testing [{client_name}] (Expected: {expected_store}) with message: '{msg_text}' ---")
        
        # We need to simulate the local variables and handler function inside register_auto_reply_handler
        # Let's call a simplified version of the logic
        is_lisansarena = "3" in client_name or "5" in client_name or "lisans" in client_name.lower()
        is_keyvadi = not is_lisansarena
        
        print(f"  Store Resolved: {'LisansArena' if is_lisansarena else 'KeyVadi'}")
        
        products = []
        if is_lisansarena:
            if os.path.exists("lisansarena_shopier_links.json"):
                with open("lisansarena_shopier_links.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        pid = item.get("id")
                        title = item.get("title")
                        url = item.get("url")
                        price_val = item.get("priceData", {}).get("price", "0")
                        price_str = f"{float(price_val):.2f} TL"
                        products.append({
                            "id": pid,
                            "title": title,
                            "price": price_str,
                            "url": url
                        })
        elif is_keyvadi:
            if os.path.exists("keyvadi_shopier_links.json"):
                with open("keyvadi_shopier_links.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        pid = item.get("id")
                        title = item.get("title")
                        url = item.get("url")
                        price_val = item.get("price", "0")
                        products.append({
                            "id": pid,
                            "title": title,
                            "price": price_val,
                            "url": url
                        })
                        
        print(f"  Loaded {len(products)} products from JSON.")
        
        matched_products = otomatik_katil.match_multiple_products_from_text(msg_text, products)
        if not matched_products:
            print("  ❌ No products matched.")
            continue
            
        if len(matched_products) == 1:
            reply_text = matched_products[0]['url']
        else:
            lines = ["🔍 **Aradığınız Ürünler:**\n"]
            for p in matched_products[:5]:
                lines.append(f"• **{p['title']}** ({p['price']}):\n  👉 {p['url']}")
            reply_text = "\n".join(lines)
            
        print(f"  [SUCCESS] Match found:")
        print(reply_text)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_simulation())
