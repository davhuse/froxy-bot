with open(r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md", "r", encoding="utf-8") as f:
    text = f.read()

import re
# Let's print any paragraph containing /v1/ or /products
matches = re.findall(r'.{0,100}/products.{0,100}', text, re.IGNORECASE)
print(f"Found {len(matches)} mentions of '/products':")
for m in set(matches)[:30]:
    print(f"- {m.strip()}")
