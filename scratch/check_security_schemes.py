import json

with open("oas_registry.json", "r", encoding="utf-8") as f:
    oas = json.load(f)

print("Security Schemes:")
components = oas.get("components", {})
security_schemes = components.get("securitySchemes", {})
print(json.dumps(security_schemes, indent=2))

print("\nGlobal Security requirement:")
print(oas.get("security"))
