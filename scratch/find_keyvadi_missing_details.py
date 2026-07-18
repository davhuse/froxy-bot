import os
import json
import csv

keywords = ["trendyol", "shell", "exxen"]
files_to_check = [
    "live_shopier_products.json",
    "created_shopier_products.json",
    "shopier_elements_products.json",
    "shopier_urunler.csv",
    "shopier_upload_log.txt",
    "bot_config.json"
]

print("Searching for Trendyol, Shell, Exxen details in KeyVadi files...")
for fname in files_to_check:
    if not os.path.exists(fname):
        continue
    print(f"\n=== File: {fname} ===")
    
    if fname.endswith(".json"):
        try:
            with open(fname, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # If it's a dict, inspect keys/values or make it a list
            if isinstance(data, dict):
                # check shopier_links
                for k, v in data.items():
                    if any(kw in k.lower() or (isinstance(v, str) and kw in v.lower()) for kw in keywords):
                        print(f"Key: {k} -> Value: {v}")
            elif isinstance(data, list):
                for idx, item in enumerate(data):
                    item_str = json.dumps(item, ensure_ascii=False).lower()
                    if any(kw in item_str for kw in keywords):
                        print(f"Item {idx}:")
                        print(json.dumps(item, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error reading JSON {fname}: {e}")
            
    elif fname.endswith(".csv"):
        try:
            with open(fname, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for idx, row in enumerate(reader):
                    row_str = " | ".join(row).lower()
                    if any(kw in row_str for kw in keywords):
                        print(f"Row {idx}: {' | '.join(row)}")
        except Exception as e:
            print(f"Error reading CSV {fname}: {e}")
            
    elif fname.endswith(".txt"):
        try:
            with open(fname, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f):
                    if any(kw in line.lower() for kw in keywords):
                        print(f"Line {idx}: {line.strip()}")
        except Exception as e:
            print(f"Error reading TXT {fname}: {e}")
            
print("\nSearch complete.")
