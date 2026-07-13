import json

with open("oas_registry.json", "r", encoding="utf-8") as f:
    oas = json.load(f)

products_path = oas.get("paths", {}).get("/products", {})
post_method = products_path.get("post", {})

print("=== POST /products API DETAILS ===")
print("Description:", post_method.get("description"))
print("Summary:", post_method.get("summary"))

request_body = post_method.get("requestBody", {})
content = request_body.get("content", {})
for ct, ct_data in content.items():
    print(f"\nContent-Type: {ct}")
    schema = ct_data.get("schema", {})
    # Resolve refs if present
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    
    print("Required properties:", required)
    print("\nProperties detail:")
    for prop_name, prop_data in properties.items():
        print(f"- {prop_name}: Type={prop_data.get('type')}, Description={prop_data.get('description')}")
        # If there are sub-properties (e.g. objects)
        if prop_data.get("type") == "object":
            print("  Sub-properties:")
            for sub_name, sub_data in prop_data.get("properties", {}).items():
                print(f"    * {sub_name}: Type={sub_data.get('type')}, Description={sub_data.get('description')}")
        elif prop_data.get("type") == "array":
            print(f"  Items: {prop_data.get('items')}")
            
# Let's check servers
print("\nServers:")
for s in oas.get("servers", []):
    print("-", s.get("url"))
