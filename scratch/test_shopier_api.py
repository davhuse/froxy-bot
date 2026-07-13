import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJiOGI0MjA0NWM1NDY2ZDdiMWQwODc0OGUzZTBkNDlmNSIsImp0aSI6Ijg1MGQwMzdmMDA2MWMyMjc4MDBkNDcxNzJmMmQ1NTMxZDQ4ODNhMjMzM2RkNTVmNmYwMDkwOGM5NmEyZjIwZDhkMzA5YmQ3YTQ5ZjM1MmViYjE1ZjdiZmMzNWIyODUxYzI0OTcxZjJjMzhkNGIzMGFlMzI3NDBlZGQzOTNhYmYzMWFkYmYyMWE4ZDAzNThlYWRiYTA3YWQwZjFjYTJlY2YiLCJpYXQiOjE3ODM5NjAzNTYsIm5iZiI6MTc4Mzk2MDM1NiwiZXhwIjoxOTQxNzQ1MTE2LCJzdWIiOjI1MDk0OTMsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.Qm7lPz2dY1-RpllpREC8mfruDPCTOnBufCz3pxSMmvEszdJlBvD0_eL_9h90DyiuTEXR6Q-Sbzt06H29tAeLGyCIRoMCgKluB69s_T6lLx5xpdV_M0KsppXIfsuxM3chcyVtYoT-qTXRFCNH3S_1jchf8CucsWdtdIfRAMINuy3IiBAAiBNPXWzsf2O2ChgPod7eIGoF5DNl2uVXWpgHJjMHb8fqw2F5CLl4Zl-7h5NiUDz5Qyhp2ZUZ2D7attYpklgOyk3mh9J7sEAyas6dqv5lMtH2lWT84BlLz5XuzM_CTKh436LEZIQWdwKp1zHjsAHJmHGmmWdwd0lylCcrwQ"

url = "https://api.shopier.com/v1/products"
print("Fetching products via API...")
try:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Authorization": f"Bearer {token}"
        }
    )
    with urllib.request.urlopen(req, context=ctx) as r:
        content = r.read().decode("utf-8")
        js = json.loads(content)
        print("Success! Number of products:", len(js))
        for p in js[:5]:
            print(f"- {p.get('id')}: {p.get('title')} ({p.get('priceData', {}).get('price')} {p.get('priceData', {}).get('currency')})")
except Exception as e:
    print("API request failed:", e)
