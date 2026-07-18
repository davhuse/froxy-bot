import urllib.request
import urllib.error
import ssl

ctx = ssl._create_unverified_context()

urls = [
    "https://www.shopier.com/48901849",
    "https://www.shopier.com/48901864",
    "https://www.shopier.com/48901866"
]

for url in urls:
    print(f"Checking {url}...")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            final_url = r.geturl()
            print(f"  Status: {r.getcode()} | Final URL: {final_url}")
            if "not_found" in final_url or "error" in final_url:
                print("  [RESULT] Product does not exist on Shopier storefront!")
            else:
                print("  [RESULT] Product exists and is LIVE!")
    except urllib.error.HTTPError as e:
        print(f"  [RESULT] Failed with HTTP Error {e.code}: {e.reason}")
    except Exception as e:
        print(f"  [RESULT] Other error: {e}")
