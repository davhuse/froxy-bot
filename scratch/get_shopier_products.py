import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

token_kv = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJiOGI0MjA0NWM1NDY2ZDdiMWQwODc0OGUzZTBkNDlmNSIsImp0aSI6Ijg1MGQwMzdmMDA2MWMyMjc4MDBkNDcxNzJmMmQ1NTMxZDQ4ODNhMjMzM2RkNTVmNmYwMDkwOGM5NmEyZjIwZDhkMzA5YmQ3YTQ5ZjM1MmViYjE1ZjdiZmMzNWIyODUxYzI0OTcxZjJjMzhkNGIzMGFlMzI3NDBlZGQzOTNhYmYzMWFkYmYyMWE4ZDAzNThlYWRiYTA3YWQwZjFjYTJlY2YiLCJpYXQiOjE3ODM5NjAzNTYsIm5iZiI6MTc4Mzk2MDM1NiwiZXhwIjoxOTQxNzQ1MTE2LCJzdWIiOjI5ODgwNTAsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.Qm7lPz2dY1-RpllpREC8mfruDPCTOnBufCz3pxSMmvEszdJlBvD0_eL_9h90DyiuTEXR6Q-Sbzt06H29tAeLGyCIRoMCgKluB69s_T6lLx5xpdV_M0KsppXIfsuxM3chcyVtYoT-qTXRFCNH3S_1jchf8CucsWdtdIfRAMINuy3IiBAAiBNPXWzsf2O2ChgPod7eIGoF5DNl2uVXWpgHJjMHb8fqw2F5CLl4Zl-7h5NiUDz5Qyhp2ZUZ2D7attYpklgOyk3mh9J7sEAyas6dqv5lMtH2lWT84BlLz5XuzM_CTKh436LEZIQWdwKp1zHjsAHJmHGmmWdwd0lylCcrwQ"
token_la = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5YjI5OWVmNzFlNTYyNDIzNDIxYTk5NDc1YzA2YWVlNiIsImp0aSI6IjkyMjYyZGFlMjliZmFkY2NhYTA1OTRmZWQ1NDg3MzQyMjA4ZTY0OGZhMTI4ZjFiYzI1OWQ1ZDI5NDczODc2ZWM0OTU2MjkyOWM3ODE4MWJjMGE1ZGIxMTNlODM3NTRmODVhNTEzNDQwMjU5YjVkNDU0N2M0YTgyZDNlMjI4ZTVmMjRkZjhhNTQ4NDQ5NGNlYzIxYjg1N2UxYWRmMmY2OWMiLCJpYXQiOjE3ODM4MDk2OTUsIm5iZiI6MTc4MzgwOTY5NSwiZXhwIjoxOTQxNTk0NDU1LCJzdWIiOjI5ODgwNTAsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.bMbTumHi1Jzjl49eZbNfY-S8X7zAYvpnPNOpLxv2RAm76ZcHJbtj_9QrCYL6Q679vtyA2SdB8vdhXmTtVRi4t7PO63Q1LDN4BQTxY5ZbxbBFrVdbkUi-9GC7QXuDcooxOuI8WC6CBqXr9pCyK3Hx-N8QCldTpmz54Hv9iyL0Y4t0ZLZ-F_-V_vWli9qTcMEODqsg-eC-dNgrqKVwdJjrQqWlMK60nNliYlTzxWJmYVjp0jmHHx6sQWRQNDy1Iu39sZefbFHqQKEJt77icupETH_-Y3h1cwSvv9aMh-kSndNrP-dYFSp6B3yWAXo6KhB19dK9HOHk-NGJNL4v4e13lQ"

def fetch_shopier_products(token, name):
    url = "https://api.shopier.com/v1/products"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            data = json.loads(response.read().decode("utf-8"))
            print(f"=== {name} Products ({len(data)}) ===")
            for p in data:
                print(f"ID: {p['id']} | Title: {p['title']} | Price: {p.get('priceData', {}).get('price')} | URL: {p.get('url')}")
    except Exception as e:
        print(f"Error fetching for {name}: {e}")

fetch_shopier_products(token_kv, "KeyVadi")
print("\n" + "="*50 + "\n")
fetch_shopier_products(token_la, "LisansArena")
