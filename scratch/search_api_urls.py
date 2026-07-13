import re
import json

path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

script_matches = re.findall(r'<script id="ssr-props" type="application/json">({.*?})</script>', html)
if script_matches:
    data = json.loads(script_matches[0])
    
    # Print keys of data['version']
    version = data.get("version", {})
    print("Version keys:", list(version.keys()))
    
    # Check if there is an openapi or apiSetting in version
    # Let's search recursively for keys that might contain OpenAPI or schema
    found_urls = set()
    def find_urls(obj):
        if isinstance(obj, str):
            if "api.shopier.com" in obj or "shopier.com/v1" in obj or "https://api" in obj:
                found_urls.add(obj)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                find_urls(v)
        elif isinstance(obj, list):
            for item in obj:
                find_urls(item)

    find_urls(data)
    print("Found URLs in JSON:", found_urls)
else:
    print("No ssr-props found.")
