import urllib.request
import urllib.error
import json
import ssl
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

token_kv = "eyJ0eXAiOiJKV1QiLCJhbGciOiJiOGI0MjA0NWM1NDY2ZDdiMWQwODc0OGUzZTBkNDlmNSIsImp0aSI6Ijg1MGQwMzdmMDA2MWMyMjc4MDBkNDcxNzJmMmQ1NTMxZDQ4ODNhMjMzM2RkNTVmNmYwMDkwOGM5NmEyZjIwZDhkMzA5YmQ3YTQ5ZjM1MmViYjE1ZjdiZmMzNWIyODUxYzI0OTcxZjJjMzhkNGIzMGFlMzI3NDBlZGQzOTNhYmYzMWFkYmYyMWE4ZDAzNThlYWRiYTA3YWQwZjFjYTJlY2YiLCJpYXQiOjE3ODM5NjAzNTYsIm5iZiI6MTc4Mzk2MDM1NiwiZXhwIjoxOTQxNzQ1MTE2LCJzdWIiOjI1MDk0OTMsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.Qm7lPz2dY1-RpllpREC8mfruDPCTOnBufCz3pxSMmvEszdJlBvD0_eL_9h90DyiuTEXR6Q-Sbzt06H29tAeLGyCIRoMCgKluB69s_T6lLx5xpdV_M0KsppXIfsuxM3chcyVtYoT-qTXRFCNH3S_1jchf8CucsWdtdIfRAMINuy3IiBAAiBNPXWzsf2O2ChgPod7eIGoF5DNl2uVXWpgHJjMHb8fqw2F5CLl4Zl-7h5NiUDz5Qyhp2ZUZ2D7attYpklgOyk3mh9J7sEAyas6dqv5lMtH2lWT84BlLz5XuzM_CTKh436LEZIQWdwKp1zHjsAHJmHGmmWdwd0lylCcrwQ"
token_la = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5YjI5OWVmNzFlNTYyNDIzNDIxYTk5NDc1YzA2YWVlNiIsImp0aSI6IjkyMjYyZGFlMjliZmFkY2NhYTA1OTRmZWQ1NDg3MzQyMjA4ZTY0OGZhMTI4ZjFiYzI1OWQ1ZDI5NDczODc2ZWM0OTU2MjkyOWM3ODE4MWJjMGE1ZGIxMTNlODM3NTRmODVhNTEzNDQwMjU5YjVkNDU0N2M0YTgyZDNlMjI4ZTVmMjRkZjhhNTQ4NDQ5NGNlYzIxYjg1N2UxYWRmMmY2OWMiLCJpYXQiOjE3ODM4MDk2OTUsIm5iZiI6MTc4MzgwOTY5NSwiZXhwIjoxOTQxNTk0NDU1LCJzdWIiOjI5ODgwNTAsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.bMbTumHi1Jzjl49eZbNfY-S8X7zAYvpnPNOpLxv2RAm76ZcHJbtj_9QrCYL6Q679vtyA2SdB8vdhXmTtVRi4t7PO63Q1LDN4BQTxY5ZbxbBFrVdbkUi-9GC7QXuDcooxOuI8WC6CBqXr9pCyK3Hx-N8QCldTpmz54Hv9iyL0Y4t0ZLZ-F_-V_vWli9qTcMEODqsg-eC-dNgrqKVwdJjrQqWlMK60nNliYlTzxWJmYVjp0jmHHx6sQWRQNDy1Iu39sZefbFHqQKEJt77icupETH_-Y3h1cwSvv9aMh-kSndNrP-dYFSp6B3yWAXo6KhB19dK9HOHk-NGJNL4v4e13lQ"

new_products = [
    {
        "title": "HBO Max 1 Aylık Profil",
        "price": 39.90,
        "desc": "HBO Max 1 Aylık Premium Profil. Size özel profil ismi ve şifreleme sağlanır.",
        "image_url": "https://picsum.photos/id/237/800/800" # High-quality static photo
    },
    {
        "title": "Prime Video (1 Aylık) - Özel Profil",
        "price": 29.90,
        "desc": "Amazon Prime Video 1 Aylık Kişisel Profil. Özel şifreli profil ile kesintisiz izleme.",
        "image_url": "https://picsum.photos/id/201/800/800"
    },
    {
        "title": "Prime Video (1 Aylık) - Ortak Profil",
        "price": 19.90,
        "desc": "Amazon Prime Video 1 Aylık Ortak Kullanım Hesabı. Giriş garantilidir.",
        "image_url": "https://picsum.photos/id/103/800/800"
    }
]

def create_products(token, store_name):
    print(f"\n--- Creating products for {store_name} ---")
    url = "https://api.shopier.com/v1/products"
    
    for idx, p in enumerate(new_products):
        payload = {
            "title": p["title"],
            "description": p["desc"],
            "type": "digital",
            "media": [
                {
                    "type": "image",
                    "url": p["image_url"],
                    "placement": 1
                }
            ],
            "priceData": {
                "currency": "TRY",
                "price": f"{p['price']:.2f}",
                "discount": False,
                "discountedPrice": f"{p['price']:.2f}",
                "shippingPrice": "0.00"
            },
            "stockQuantity": 999,
            "shippingPayer": "sellerPays"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        print(f"[{idx+1}/{len(new_products)}] Creating: {p['title']} ({p['price']} TL)...")
        try:
            with urllib.request.urlopen(req, context=ctx) as r:
                res = json.loads(r.read().decode("utf-8"))
                print(f"  [SUCCESS] Product ID: {res.get('id')} | URL: {res.get('url')}")
        except urllib.error.HTTPError as e:
            print(f"  [FAILED] HTTP Error {e.code}: {e.reason}")
            try:
                print("  Response Body:", e.read().decode("utf-8"))
            except:
                pass
        except Exception as e:
            print(f"  [FAILED] Other error: {e}")
        time.sleep(2.0)

# Create for both stores
create_products(token_kv, "KeyVadi")
create_products(token_la, "LisansArena")
