import urllib.request
import json
import ssl
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Copy exact token string
token_parts = [
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.",
    "eyJhdWQiOiJmOTMzYTA0MDk0ZmZhZjU0MTBkMmU3Y2UxNzk5NTQ4MCIsImp0aSI6IjQxMWFmY2Q2MmM5M2YyZjUyMjgyYzMyOWQyZjgzY2VjOGYwNGZiZGExNjk5NWY2ZGIxMTcxMTZmODVhMzM3OGY0YzdjMzU2YWQ2ZTRlZGJhODhlMjNlYWM5ZWJiOWM3Y2YwYTNhZDU3MjI3Y2VhZTYyYzVmYTdlNTFjNjc3MmJiMmQxOTAxNmExNzJmZDgyN2VlNWI5YmNhZWE5MTIzMzIiLCJpYXQiOjE3ODU1OTE5OTEsIm5iZiI6MTc4NTU5MTk5MSwiZXhwIjoxOTQzMzc2NzUxLCJzdWIiOjI5NDM0ODgsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.",
    "K3M_7VAolrHesADviFrbwloJmDnSvLDTcTRw2SBRWkeXuH_JQ9l9yL-il78U2yMO002BL2w9IHUk6SbNsCTuP8pB5e7WUE-V08DGcy6jDkL2_2NitRFhaQXC9hnxBWKIEogOfxtQSWhVd_c8525bRZ6OF4KQP8tTwTYJYOSkXX2eRFZ2peLJYuUUKSuqv6HZ-dj7kQ9MNP_HSdWdW9-QXaLP5O-9mdIj0Wa8OT_cw0cHsuFvluMfgfRaRp0mTmoAvLK3LE_FPsTc3WJ98Slw7pU7gc14mjlt79rx_KjEnRgyjBe3oA9XZjNYxze3hAKUelrCaOU-DTj9fG4WUArviw"
]
real_token = "".join(token_parts)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Test 1: POST /v1/products without media
print("Testing POST /v1/products WITHOUT media...")
payload1 = {
    "title": "Gemini Pro 12 Aylik Davet",
    "type": "digital",
    "description": "Gemini Pro 12 Aylik Davet Hesabi. Maksimum 1 Ay Garanti Mevcuttur.",
    "priceData": {
        "currency": "TRY",
        "price": "59.99",
        "discount": False,
        "discountedPrice": "59.99",
        "shippingPrice": "0.00"
    },
    "stockQuantity": 999,
    "shippingPayer": "sellerPays"
}

req1 = urllib.request.Request('https://api.shopier.com/v1/products', data=json.dumps(payload1).encode('utf-8'), headers={
    'Authorization': f'Bearer {real_token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0'
})

try:
    with urllib.request.urlopen(req1, context=ctx) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("🎉🎉🎉 SUCCESS CREATED PRODUCT WITHOUT MEDIA!")
        print("ID:", res.get("id"))
        print("Link: https://www.shopier.com/" + str(res.get("id")))
except urllib.error.HTTPError as e:
    print("❌ POST 1 HTTP Error:", e.code, e.read().decode('utf-8'))

# Test 2: POST /v1/products with media URL
print("\nTesting POST /v1/products WITH media...")
payload2 = {
    "title": "Gemini Pro 18 Aylik Davet",
    "type": "digital",
    "description": "Gemini Pro 18 Aylik Davet Hesabi. Maksimum 1 Ay Garanti Mevcuttur.",
    "media": [
        {
            "type": "image",
            "url": "https://i.ibb.co/3s8vL0h/gemini.jpg",
            "placement": 1
        }
    ],
    "priceData": {
        "currency": "TRY",
        "price": "99.99",
        "discount": False,
        "discountedPrice": "99.99",
        "shippingPrice": "0.00"
    },
    "stockQuantity": 999,
    "shippingPayer": "sellerPays"
}

req2 = urllib.request.Request('https://api.shopier.com/v1/products', data=json.dumps(payload2).encode('utf-8'), headers={
    'Authorization': f'Bearer {real_token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0'
})

try:
    with urllib.request.urlopen(req2, context=ctx) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("🎉🎉🎉 SUCCESS CREATED PRODUCT WITH MEDIA!")
        print("ID:", res.get("id"))
        print("Link: https://www.shopier.com/" + str(res.get("id")))
except urllib.error.HTTPError as e:
    print("❌ POST 2 HTTP Error:", e.code, e.read().decode('utf-8'))
