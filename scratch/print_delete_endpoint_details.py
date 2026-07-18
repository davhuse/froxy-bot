import json
import re

path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

script_matches = re.findall(r'<script id="ssr-props" type="application/json">({.*?})</script>', html)
if script_matches:
    data = json.loads(script_matches[0])
    ref = data.get("refCategories", [])
    
    def print_doc(doc):
        if doc.get("slug") == "delete-products-id":
            print("FOUND delete-products-id:")
            print(json.dumps(doc, indent=2, ensure_ascii=False))
            return True
        children = doc.get("children", [])
        for ch in children:
            if print_doc(ch):
                return True
        return False

    for cat in ref:
        pages = cat.get("pages", [])
        for p in pages:
            if print_doc(p):
                break
