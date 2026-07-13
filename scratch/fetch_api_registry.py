import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = [
    "https://api.readme.com/v1/api-registry/j3dkh16m5ushkhl",
    "https://dash.readme.com/api/v1/api-registry/j3dkh16m5ushkhl",
    "https://developer.shopier.com/api/v1/api-registry/j3dkh16m5ushkhl",
]

for url in urls:
    print(f"Downloading from {url}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx) as r:
            content = r.read().decode("utf-8")
            print("Successfully downloaded! Content length:", len(content))
            with open("oas_registry.json", "w", encoding="utf-8") as f:
                f.write(content)
            
            js = json.loads(content)
            print("JSON keys:", list(js.keys())[:10])
            if "paths" in js:
                print("OAS Paths:", list(js["paths"].keys()))
            break
    except Exception as e:
        print("Failed:", e)
