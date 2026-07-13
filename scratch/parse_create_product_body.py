import re
import json

path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

script_matches = re.findall(r'<script id="ssr-props" type="application/json">({.*?})</script>', html)
if script_matches:
    data = json.loads(script_matches[0])
    # Let's inspect data keys
    print("Keys of data:", list(data.keys()))
    # Let's check apiSettings
    api_settings = data.get("apiSettings", [])
    print("apiSettings count:", len(api_settings))
    for setting in api_settings:
        print("apiSetting:", setting.get("_id"), setting.get("baseUrl"), setting.get("title"))
        
    # Let's search for "post-products" or "products" in raw json to find any references
    raw_json = script_matches[0]
    # Let's look for "url" or "post" and "/products"
    for m in re.finditer(r'"url"\s*:\s*"/products"', raw_json):
        idx = m.start()
        print("Found /products url in raw json!")
        print(raw_json[idx-100:idx+300])
else:
    print("No ssr-props found.")
