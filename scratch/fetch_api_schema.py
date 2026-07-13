import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Let's try downloading from developer.shopier.com api-endpoints.json or registry
urls = [
    "https://developer.shopier.com/api-endpoints.json",
    "https://developer.shopier.com/api-registry/j3dkh16m5ushkhl",
]

for url in urls:
    print(f"Downloading from {url}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx) as r:
            content = r.read().decode("utf-8")
            print("Successfully downloaded! Content length:", len(content))
            # Let's save it
            filename = url.split("/")[-1]
            if not filename.endswith(".json"):
                filename += ".json"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Let's parse it and find post-products
            try:
                js = json.loads(content)
                print("JSON parsed! Keys:", list(js.keys())[:10])
                if "paths" in js:
                    print("OAS Paths in JSON:", list(js["paths"].keys()))
            except Exception as pe:
                print("Failed to parse as JSON:", pe)
    except Exception as e:
        print("Failed:", e)
