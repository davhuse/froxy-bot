import re
import json

path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

# Find the apiBaseUrl
api_base_url_match = re.search(r'"apiBaseUrl"\s*:\s*"([^"]+)"', html)
if api_base_url_match:
    print("API Base URL:", api_base_url_match.group(1))

# Find the ssr-props JSON block
script_matches = re.findall(r'<script id="ssr-props" type="application/json">({.*?})</script>', html)
if script_matches:
    data = json.loads(script_matches[0])
    
    # We want to search for documentation pages or endpoints.
    # Let's find pages under refCategories -> API ENDPOINTS -> pages -> Products -> children
    ref = data.get("refCategories", [])
    for cat in ref:
        if cat.get("title") == "API ENDPOINTS":
            pages = cat.get("pages", [])
            for p in pages:
                if p.get("title") == "Products":
                    print("Found Products page!")
                    children = p.get("children", [])
                    for child in children:
                        print(f"Child Page: {child.get('title')} (slug: {child.get('slug')})")
                        api_info = child.get("api", {})
                        print("  Method:", api_info.get("method"))
                        print("  URL:", api_info.get("url"))
                        print("  Params:", api_info.get("params"))
                        print("  Body Empty:", child.get("isBodyEmpty"))
                        
                        # Let's see if there is markdown or html content that details the body parameters
                        # In Readme.io, parameters are sometimes in the 'api' field under 'params' or custom fields.
                        # Let's inspect the entire child dict fields
                        for k, v in child.items():
                            if k not in ["html", "body", "markdown"]:
                                print(f"    {k}: {str(v)[:300]}")
                            else:
                                # Search for parameter names in html
                                print(f"    {k} (length: {len(v)}):")
                                # Print all matches of words inside quotes or table headers in v
                                params = re.findall(r'"name"\s*:\s*"([^"]+)"', v)
                                if params:
                                    print("      Params in text:", set(params))
                                
else:
    print("No ssr-props found.")
