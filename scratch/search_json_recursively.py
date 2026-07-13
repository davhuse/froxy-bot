import re
import json

path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

script_matches = re.findall(r'<script id="ssr-props" type="application/json">({.*?})</script>', html)
if script_matches:
    data = json.loads(script_matches[0])
    
    # We want to find any text field containing "Create a product" or "post-products" in the entire JSON data
    found_nodes = []
    
    def search_dict(d, path_str=""):
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, str) and ("post-products" in v or "Create a product" in v):
                    found_nodes.append((path_str + "." + k, v))
                else:
                    search_dict(v, path_str + "." + k)
        elif isinstance(d, list):
            for i, item in enumerate(d):
                search_dict(item, path_str + f"[{i}]")

    search_dict(data)
    for path, val in found_nodes:
        print(f"Path: {path}")
        print(f"Val: {str(val)[:300]}")
        print("-" * 50)
else:
    print("No ssr-props found.")
