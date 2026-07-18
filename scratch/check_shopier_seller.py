import urllib.request
import ssl

ctx = ssl._create_unverified_context()
url = "https://www.shopier.com/49002143"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

try:
    with urllib.request.urlopen(req, context=ctx) as r:
        html = r.read().decode("utf-8")
        # Search for seller name or shop name in html
        # Often there's a shop link like /keyvadi or /lisansarena
        print("keyvadi in html:", "keyvadi" in html.lower())
        print("lisansarena in html:", "lisansarena" in html.lower())
        
        # Print a snippet of html with seller or shop mentions
        for line in html.split("\n"):
            if "shopname" in line.lower() or "seller" in line.lower() or "mağaza" in line.lower() or "magaza" in line.lower():
                print(line.strip()[:150])
except Exception as e:
    print("Error:", e)
