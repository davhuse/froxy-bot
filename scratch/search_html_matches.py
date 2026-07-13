import re

path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\steps\10891\content.md"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

# Search for j3dkh16m5ushkhl or api-endpoints.json in html
for m in re.finditer(r'j3dkh16m5ushkhl|api-endpoints\.json', html):
    idx = m.start()
    print("Match found in HTML at index:", idx)
    print(html[idx-100:idx+500])
