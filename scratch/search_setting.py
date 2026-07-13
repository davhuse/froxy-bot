import re
import json

path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

script_matches = re.findall(r'<script id="ssr-props" type="application/json">({.*?})</script>', html)
if script_matches:
    data = json.loads(script_matches[0])
    
    # Search for setting 62b9b43172164000486fc41a recursively
    def find_doc(obj, target_id):
        if isinstance(obj, dict):
            if obj.get("_id") == target_id:
                return obj
            for k, v in obj.items():
                res = find_doc(v, target_id)
                if res:
                    return res
        elif isinstance(obj, list):
            for item in obj:
                res = find_doc(item, target_id)
                if res:
                    return res
        return None

    doc = find_doc(data, "62b9b43172164000486fc41a")
    if doc:
        print("=== FOUND SETTING ===")
        for k, v in doc.items():
            print(f"{k}: {str(v)[:500]}")
    else:
        print("Setting not found recursively")
else:
    print("No ssr-props found.")
