import urllib.request
import urllib.error
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5YjI5OWVmNzFlNTYyNDIzNDIxYTk5NDc1YzA2YWVlNiIsImp0aSI6IjkyMjYyZGFlMjliZmFkY2NhYTA1OTRmZWQ1NDg3MzQyMjA4ZTY0OGZhMTI4ZjFiYzI1OWQ1ZDI5NDczODc2ZWM0OTU2MjkyOWM3ODE4MWJjMGE1ZGIxMTNlODM3NTRmODVhYjVkNDU0N2M0YTgyZDNlMjI4ZTVmMjRkZjhhNTQ4NDQ5NGNlYzIxYjg1N2UxYWRmMmY2OWMiLCJpYXQiOjE3ODM4MDk2OTUsIm5iZiI6MTc4MzgwOTY5NSwiZXhwIjoxOTQxNTk0NDU1LCJzdWIiOjI5ODgwNTAsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.bMbTumHi1Jzjl49eZbNfY-S8X7zAYvpnPNOpLxv2RAm76ZcHJbtj_9QrCYL6Q679vtyA2SdB8vdhXmTtVRi4t7PO63Q1LDN4BQTxY5ZbxbBFrVdbkUi-9GC7QXuDcooxOuI8WC6CBqXr9pCyK3Hx-N8QCldTpmz54Hv9iyL0Y4t0ZLZ-F_-V_vWli9qTcMEODqsg-eC-dNgrqKVwdJjrQqWlMK60nNliYlTzxWJmYVjp0jmHHx6sQWRQNDy1Iu39sZefbFHqQKEJt77icupETH_-Y3h1cwSvv9aMh-kSndNrP-dYFSp6B3yWAXo6KhB19dK9HOHk-NGJNL4v4e13lQ"

url = "https://api.shopier.com/v1/products?limit=1"

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json"
}

req = urllib.request.Request(url, headers=headers, method="GET")

print("Testing Shopier GET products endpoint...")
try:
    with urllib.request.urlopen(req, context=ctx) as r:
        res_body = r.read().decode("utf-8")
        print("Success! Response:")
        print(res_body[:500])
except urllib.error.HTTPError as e:
    print(f"Failed with HTTP Error {e.code}: {e.reason}")
    try:
        print("Body:", e.read().decode("utf-8"))
    except:
        pass
except Exception as e:
    print("Other error:", e)
