import re
import json

path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

script_matches = re.findall(r'<script id="ssr-props" type="application/json">({.*?})</script>', html)
if script_matches:
    data = json.loads(script_matches[0])
    
    # Let's search for "post-products" page in the entire JSON structure recursively
    def find_doc(obj, target_slug):
        if isinstance(obj, dict):
            if obj.get("slug") == target_slug:
                return obj
            for k, v in obj.items():
                res = find_doc(v, target_slug)
                if res:
                    return res
        elif isinstance(obj, list):
            for item in obj:
                res = find_doc(item, target_slug)
                if res:
                    return res
        return None

    doc = find_doc(data, "post-products")
    if doc:
        print("=== FOUND DOC ===")
        # Print all keys
        for k, v in doc.items():
            if k not in ["html", "body"]:
                print(f"{k}: {str(v)[:300]}")
            else:
                print(f"{k} length: {len(v)}")
                # If there's any text in them, print a sample
                print(f"{k} sample: {v[:1000]}")
    else:
        print("post-products doc not found recursively")
else:
    print("No ssr-props found.")
