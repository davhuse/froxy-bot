import json

with open("oas_registry.json", "r", encoding="utf-8") as f:
    oas = json.load(f)

products_path = oas.get("paths", {}).get("/products", {})
get_method = products_path.get("get", {})

print("=== GET /products API DETAILS ===")
print("Description:", get_method.get("description"))
print("Summary:", get_method.get("summary"))
print("Parameters:")
for param in get_method.get("parameters", []):
    print(f"- {param.get('name')} (in: {param.get('in')}): Type={param.get('schema', {}).get('type')}, Required={param.get('required')}")
