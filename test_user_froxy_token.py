import urllib.request
import json
import ssl

token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJmOTMzYTA0MDk0ZmZhZjU0MTBkMmU3Y2UxNzk5NTQ4MCIsImp0aSI6Ijc4MmU4ODcxZWJjN2Y0MDZjM2M5ZjhjNmM0ZWYzNzYxZGY0MTI1YjljZjI0NDc0MTZhMWE1MTJiMmNiYjRhZGZlNjI5YTZiNjc2NDI3ZmE1NDE3MDk1MTM5NTNhYjM1NDIwMDRjZDg1YTM3YzZiZDM5MTg0NjEyZDA3NWFhY2Y3ZDM5YzM4OWM2OTMzMDRkYjZlMzI4NmQ3NzU3NGUyNDMiLCJpYXQiOjE3ODgzMDM0MTAsIm5iZiI6MTc4ODMwMzQxMCwiZXhwIjoxOTQ2MDg4MTcwLCJzdWIiOjI5NDM0ODgsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.uTicrPhDBrpXdMSnLRlAIfsegUSl3WkJPYxpWf3W2QC_dDXQajpA6Rmw7x7ySRJo958vSADGKoSDX700Vx9AvUumbOQRRa20ZwJ5UIyqUkc_M_yOGYGCszug9RDEMwEpS_va3tQM4cU3LPOPkC53APwjGRhQRanrw-8RfZBsaUrGidJgRdLY-G0gJk6f5Tq7_3NfPPuq-CCS8l6PXwm2GsM74Pp7SNJLmUz1vG3VY0JXjzah4reC_RxjfRziHK5diweU3-Nmn7iEoyI2Bp-Itfpq0t_27ECjIaxWBom18DUmaMbPkU-8tdqS9YONQUtZ6H-jRJcMzeVPlI7rVaN-9w"

import requests
h = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}
payload = {
    "title": "Froxy AI Test Bakiye",
    "type": "digital",
    "description": "Test",
    "stockQuantity": 1,
    "shippingPayer": "sellerPays",
    "priceData": {
        "currency": "TRY",
        "price": 10.0,
        "discount": False,
        "shippingPrice": 0.0
    },
    "media": [{"type": "image", "url": "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp_froxy/assets/froxy_logo.png", "placement": 1}]
}
r = requests.post("https://api.shopier.com/v1/products", headers=h, json=payload, timeout=10)
print("Shopier Response Code:", r.status_code)
print("Shopier Response Body:", r.text)
if r.status_code in (200, 201):
    pid = r.json().get("id")
    print("Froxy Shopier Product created! Cleaning up:", pid)
    requests.delete(f"https://api.shopier.com/v1/products/{pid}", headers=h, timeout=5)
