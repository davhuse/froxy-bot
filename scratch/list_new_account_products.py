import urllib.request
import urllib.error
import json
import ssl

ctx = ssl._create_unverified_context()

# Token from replace_keyvadi_only.py which we know is 100% working
token_kv = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJiOGI0MjA0NWM1NDY2ZDdiMWQwODc0OGUzZTBkNDlmNSIsImp0aSI6IjllZDI4ZTU3ZjZkOTFjOWFjZTRjN2Y0YzNhZmUyZjg3YTg0NWEyZDAxNzdiNDgxZTlkNWE2OTAwZTY4YjVkYzliN2UxY2UwNmQ4YzYxZjQ3YTA2ZWJkOGEyMGJhMGNlMTM3ZDFjNDI0N2VhNGQzNzNhYzQ4YTFhYzBhZDIxOGM1YzVkZWM1ZGNiOTlkNjdlM2M5NTJjYjFjMWU5ZjlmZjMiLCJpYXQiOjE3ODQxMjIzODIsIm5iZiI6MTc4NDEyMjM4MiwiZXhwIjoxOTQxOTA3MTQyLCJzdWIiOjI1MDk0OTMsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.jdLI_JWWU1MlRz4A4vxKj0EtfeffmuJFzO8Eq3YC2aWiY1MFEZZ8x6HQdSiqdB3JY1U4Sirk8cVfysm1FU9ulCtrtcviPztPQWWGL0AGgbqRDlc2uw4YhuPzLIIafA_Ej1O_BIDI48UOK6LpvBWapMjISa23Jjj5MLISvYRH9lMS_v2IUDpjvsf-6H6Bpi1BCNvSlLoMRT8_SPnqPY3908zsm3xZvPfENBQAtpdvydAdFVtq-EaNesit5gWER8NaUickGDZ7_G7KOdF-08Ej4YOAxly_HvWaO8Gi_JzKqYnMgd66d-snGOpj0pIvsqKmRmdHJ53tflFF_X363dKaBg"

url = "https://api.shopier.com/v1/products?limit=100"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Authorization": f"Bearer {token_kv}",
    "Accept": "application/json"
}

req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, context=ctx) as r:
        res = json.loads(r.read().decode("utf-8"))
        print(f"Total products in new account: {len(res)}")
        for p in res[:15]:
            print(f"- {p.get('title')} ({p.get('id')}) -> {p.get('url')}")
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.reason)
    print("Body:", e.read().decode("utf-8"))
except Exception as e:
    print("Error:", e)
