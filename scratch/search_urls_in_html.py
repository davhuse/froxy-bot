import re

path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

# Search for any URL (http/https) in the html containing j3dkh16m5ushkhl or api-endpoints.json
urls = re.findall(r'https?://[^\s"\'<>]+(?:j3dkh16m5ushkhl|api-endpoints\.json)[^\s"\'<>]*', html)
print("Found URLs:", set(urls))

# Search for any string starting with https?:// in the JSON
import json
script_matches = re.findall(r'<script id="ssr-props" type="application/json">({.*?})</script>', html)
if script_matches:
    data = json.loads(script_matches[0])
    
    found_urls = set()
    def find_all_urls(obj):
        if isinstance(obj, str):
            if obj.startswith("http"):
                found_urls.add(obj)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                find_all_urls(v)
        elif isinstance(obj, list):
            for item in obj:
                find_all_urls(item)
    find_all_urls(data)
    
    print("All URLs in ssr-props:")
    for u in found_urls:
        if "api" in u or "registry" in u or "readme" in u:
            print(" -", u)
