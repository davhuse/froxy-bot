import re
import json

path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

# Let's search for any occurrence of "products" in raw json to find all snippets
script_matches = re.findall(r'<script id="ssr-props" type="application/json">({.*?})</script>', html)
if script_matches:
    raw_json = script_matches[0]
    
    # Search for all strings starting with /v1/ or containing /products
    matches = re.findall(r'"[^"]*/products[^"]*"', raw_json)
    print("Matches for products in strings:", set(matches))
    
    # Search for all occurrences of "v1"
    matches_v1 = re.findall(r'"[^"]*/v1/[^"]*"', raw_json)
    print("Matches for /v1/ in strings:", set(matches_v1))
    
    # Let's search for "baseUrl"
    matches_url = re.findall(r'"[^"]*Url[^"]*"\s*:\s*"[^"]*"', raw_json)
    print("Matches for Url keys:", set(matches_url))
else:
    print("No ssr-props found.")
