import urllib.request, re

req = urllib.request.Request('https://www.shopier.com/lisansarena/49847044', headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')

# Check if product is marked as no-stock or if form is active:
print("Is no-stock present?")
for m in re.finditer(r'class="[^"]*no-stock[^"]*"', html):
    start = max(0, m.start() - 100)
    end = min(len(html), m.end() + 100)
    print("Snippet:", html[start:end])

forms = re.findall(r'<form[^>]*>(.*?)</form>', html, re.DOTALL)
print(f"\nForms found: {len(forms)}")
for i, f in enumerate(forms):
    print(f"Form {i} inputs:")
    inputs = re.findall(r'<input[^>]+>', f)
    for inp in inputs:
        print("  ", inp)
    buttons = re.findall(r'<button[^>]*>(.*?)</button>', f, re.DOTALL)
    for btn in buttons:
        print("   Button:", re.sub(r'\s+', ' ', btn).strip())
