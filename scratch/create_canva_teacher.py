import urllib.request
import urllib.error
import json
import ssl
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 1. Load active tokens
tokens_path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\saved_shopier_tokens.json"
if not os.path.exists(tokens_path):
    print("Error: saved_shopier_tokens.json not found!")
    sys.exit(1)
    
with open(tokens_path, "r", encoding="utf-8") as f:
    tokens = json.load(f)
    
token_kv = tokens.get("keyvadi")
token_la = tokens.get("lisansarena")

# 2. Define the product details
p_title = "Canva Pro Öğretmen (1 Yıllık)"
p_desc = "Canva Pro Öğretmen 1 Yıllık Üyelik. Kendi mail adresinize tanımlanır. Sınıf açıp öğrenci ekleme yetkisi mevcuttur."
p_price = 149.99
p_image = "https://veridia-bot.onrender.com/static/la_canva.png"

url = "https://api.shopier.com/v1/products"

def create_product(token, store_name):
    print(f"\n--- Creating Canva Pro Teacher product for {store_name} ---")
    payload = {
        "title": p_title,
        "description": p_desc,
        "type": "digital",
        "media": [
            {
                "type": "image",
                "url": p_image,
                "placement": 1
            }
        ],
        "priceData": {
            "currency": "TRY",
            "price": f"{p_price:.2f}",
            "discount": False,
            "discountedPrice": f"{p_price:.2f}",
            "shippingPrice": "0.00"
        },
        "stockQuantity": 999,
        "shippingPayer": "sellerPays"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            res = json.loads(r.read().decode("utf-8"))
            pid = res.get("id")
            purl = res.get("url")
            print(f"  [SUCCESS] Product ID: {pid} | URL: {purl}")
            return pid, purl
    except urllib.error.HTTPError as e:
        print(f"  [FAILED] HTTP Error {e.code}: {e.reason}")
        try:
            print("  Response Body:", e.read().decode("utf-8"))
        except:
            pass
    except Exception as e:
        print(f"  [FAILED] Other error: {e}")
    return None, None

def update_links_file(file_path, pid, purl, is_la=False):
    if not os.path.exists(file_path):
        print(f"Links file {file_path} not found.")
        return
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Check if product already exists in JSON to avoid duplicates
    for item in data:
        if item.get("id") == str(pid) or item.get("title") == p_title:
            print(f"Product already exists in {file_path}")
            return
            
    if is_la:
        # LisansArena uses a more detailed structure
        new_item = {
            "id": str(pid),
            "title": p_title,
            "description": p_desc,
            "type": "digital",
            "url": purl,
            "media": [
                {
                    "id": "1",
                    "type": "image",
                    "url": p_image,
                    "placement": 1
                }
            ],
            "priceData": {
                "currency": "TRY",
                "price": f"{p_price:.2f}",
                "discount": False,
                "discountedPrice": f"{p_price:.2f}",
                "shippingPrice": "0.00"
            },
            "stockStatus": "inStock",
            "stockQuantity": 999,
            "shippingPayer": "sellerPays"
        }
    else:
        # KeyVadi uses a simpler structure
        new_item = {
            "id": str(pid),
            "title": p_title,
            "price": f"{p_price:.2f} TL",
            "url": purl
        }
        
    data.insert(0, new_item)  # Put at the beginning
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Updated {file_path} with new product.")

# Create on KeyVadi
kv_id, kv_url = create_product(token_kv, "KeyVadi")
if kv_id:
    update_links_file("keyvadi_shopier_links.json", kv_id, kv_url, is_la=False)

# Create on LisansArena
la_id, la_url = create_product(token_la, "LisansArena")
if la_id:
    update_links_file("lisansarena_shopier_links.json", la_id, la_url, is_la=True)

# Save result to a file for referencing later
if kv_id or la_id:
    with open("canva_teacher_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "keyvadi": {"id": kv_id, "url": kv_url},
            "lisansarena": {"id": la_id, "url": la_url}
        }, f, indent=2)
    print("Saved Canva Teacher results to canva_teacher_results.json")
