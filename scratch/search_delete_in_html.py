with open(r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md", "r", encoding="utf-8") as f:
    html = f.read()

# Find the index of "delete-products-id"
idx = html.find("delete-products-id")
if idx != -1:
    print("Found delete-products-id in html!")
    # Print 2000 chars around it
    print(html[idx-500:idx+2500])
else:
    print("Not found in html.")
