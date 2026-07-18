with open(r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md", "r", encoding="utf-8") as f:
    text = f.read()

import re
# Let's search for any occurrence of DELETE in the readable markdown/HTML text (outside the script tag)
# Strip script tags first
clean_text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL)

# Let's find any occurrences of delete and product
matches = []
for line in clean_text.splitlines():
    if "delete" in line.lower() and "product" in line.lower():
        matches.append(line)

print(f"Found {len(matches)} matching lines:")
for m in matches[:20]:
    print("-", m[:200])
