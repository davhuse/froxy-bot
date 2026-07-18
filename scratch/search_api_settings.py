import json
import re

path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

script_matches = re.findall(r'<script id="ssr-props" type="application/json">({.*?})</script>', html)
if script_matches:
    data = json.loads(script_matches[0])
    
    # Search for apiSettings or search the whole json for "62b9b43172164000486fc41a"
    def find_val(obj, key_to_find):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == key_to_find or str(v) == key_to_find:
                    print(f"Found key/val '{key_to_find}' in dict under key '{k}':", str(obj)[:300])
                find_val(v, key_to_find)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                find_val(item, key_to_find)
                
    print("Searching for apiSetting info...")
    find_val(data, "62b9b43172164000486fc41a")
    
    # Let's also print all keys at root level of data
    print("\nRoot keys in data:", list(data.keys()))
    if "apiSettings" in data:
        print("apiSettings:", json.dumps(data["apiSettings"], indent=2))
else:
    print("No ssr-props found.")
