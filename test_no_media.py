import urllib.request
import json
import ssl
import sys

sys.stdout.reconfigure(encoding='utf-8')

# EXACT UNTOUCHED TOKEN FROM USER MESSAGE
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJmOTMzYTA0MDk0ZmZhZjU0MTBkMmU3Y2UxNzk5NTQ4MCIsImp0aSI6IjQxMWFmY2Q2MmM5M2YyZjUyMjgyYzMyOWQyZjgzY2VjOGYwNGZiZGExNjk5NWY2ZGIxMTcxMTZmODVhMzM3OGY0YzdjMzU2YWQ2ZTRlZGJhODhlMjNlYWM5ZWJiOWM3Y2YwYTNhZDU3MjI3Y2VhZTYyYzVmYTdlNTFjNjc3MmJiMmQxOTAxNmExNzJmZDgyN2VlNWI5YmNhZWE5MTIzMzIiLCJpYXQiOjE3ODU1OTE5OTEsIm5iZiI6MTc4NTU5MTk5MSwiZXhwIjoxOTQzMzc2NzUxLCJzdWIiOjI5NDM0ODgsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.K3M_7VAolrHesADviFrbwloJmDnSvLDTcTRw2SBRWkeXuH_JQ9l9yL-il78U2yMO002BL2w9IHUk6SbNsCTuP8pB5e7WUE-V08DGcy6jDkL2_2NitRFhaQXC9hnxBWKIEogOfxtQSWhVd_c8525bRZ6OF4KQP8tTwTYJYOSkXX2eRFZ2peLJYuUUKSuqv6HZ-dj7kQ9MNP_HSdWdW9-QXaLP5O-9mdIj0Wa8OT_cw0cHsuFvluMfgfRaRp0mTmoAvLK3LE_FPsTc3WJ98Slw7pU7gc14mjlt79rx_KjEnRgyjBe3oA9XZjNYxze3hAKUelrCaOU-DTj9fG4WUArviw"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Test 1: Empty media list
payload1 = {
    'title': 'Test Product No Media 1',
    'type': 'digital',
    'description': 'Test',
    'media': [],
    'priceData': {'currency': 'TRY', 'price': '10.00', 'discount': False, 'discountedPrice': '10.00', 'shippingPrice': '0.00'},
    'stockQuantity': 99,
    'shippingPayer': 'sellerPays'
}

# Test 2: Omitted media field
payload2 = {
    'title': 'Test Product No Media 2',
    'type': 'digital',
    'description': 'Test',
    'priceData': {'currency': 'TRY', 'price': '10.00', 'discount': False, 'discountedPrice': '10.00', 'shippingPrice': '0.00'},
    'stockQuantity': 99,
    'shippingPayer': 'sellerPays'
}

for idx, p in enumerate([payload1, payload2]):
    req = urllib.request.Request('https://api.shopier.com/v1/products', data=json.dumps(p).encode('utf-8'), headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    })
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            print(f'🎉 TEST {idx+1} SUCCESS! Created ID:', res.get('id'))
    except urllib.error.HTTPError as e:
        print(f'❌ TEST {idx+1} ERROR:', e.code, e.read().decode('utf-8'))
