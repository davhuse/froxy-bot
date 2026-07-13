import re
import json

path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

script_matches = re.findall(r'<script id="ssr-props" type="application/json">({.*?})</script>', html)
if script_matches:
    data = json.loads(script_matches[0])
    
    version = data.get("version", {})
    api_registries = version.get("apiRegistries", [])
    print("apiRegistries count:", len(api_registries))
    for reg in api_registries:
        print("Registry keys:", list(reg.keys()))
        # Print first few fields
        for k, v in reg.items():
            if k not in ["oas"]:
                print(f"  {k}: {v}")
            else:
                print("  oas keys:", list(v.keys()))
                # Let's search inside OAS for paths
                paths = v.get("paths", {})
                print("  OAS Paths:", list(paths.keys()))
                # For each path, print methods
                for path_url, path_data in paths.items():
                    print(f"    {path_url} methods: {list(path_data.keys())}")
                    # Let's print requestBody schema if present
                    for method, method_data in path_data.items():
                        print(f"      Method: {method}")
                        req_body = method_data.get("requestBody", {})
                        content = req_body.get("content", {})
                        for ct, ct_data in content.items():
                            print(f"        Content-Type: {ct}")
                            schema = ct_data.get("schema", {})
                            print(f"          Properties: {list(schema.get('properties', {}).keys())}")
                            # Let's print full properties
                            print(json.dumps(schema.get('properties', {}), indent=10))
else:
    print("No ssr-props found.")
