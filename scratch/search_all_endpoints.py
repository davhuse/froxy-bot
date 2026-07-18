import re

path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md"

with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Let's find all HTTP methods (GET, POST, PUT, DELETE, PATCH) followed by endpoints in the text
methods = re.findall(r'(GET|POST|PUT|DELETE|PATCH)\s+([^\s`"]+)', text, re.IGNORECASE)
print(f"Found {len(methods)} HTTP method references in developer portal docs:")
for m in set(methods):
    print(f"- {m[0].upper()} {m[1]}")
