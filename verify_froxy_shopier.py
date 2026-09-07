import urllib.request
import json
import ssl

token_parts = [
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.",
    "eyJhdWQiOiJmOTMzYTA0MDk0ZmZhZjU0MTBkMmU3Y2UxNzk5NTQ4MCIsImp0aSI6IjQxMWFmY2Q2MmM5M2YyZjUyMjgyYzMyOWQyZjgzY2VjOGYwNGZiZGExNjk5NWY2ZGIxMTcxMTZmODVhMzM3OGY0YzdjMzU2YWQ2ZTRlZGJhODhlMjNlYWM5ZWJiOWM3Y2YwYTNhZDU3MjI3Y2VhZTYyYzVmYTdlNTFjNjc3MmJiMmQxOTAxNmExNzJmZDgyN2VlNWI5YmNhZWE5MTIzMzIiLCJpYXQiOjE3ODU1OTE5OTEsIm5iZiI6MTc4NTU5MTk5MSwiZXhwIjoxOTQzMzc2NzUxLCJzdWIiOjI5NDM0ODgsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.",
    "K3M_7VAolrHesADviFrbwloJmDnSvLDTcTRw2SBRWkeXuH_JQ9l9yL-il78U2yMO002BL2w9IHUk6SbNsCTuP8pB5e7WUE-V08DGcy6jDkL2_2NitRFhaQXC9hnxBWKIEogOfxtQSWhVd_c8525bRZ6OF4KQP8tTwTYJYOSkXX2eRFZ2peLJYuUUKSuqv6HZ-dj7kQ9MNP_HSdWdW9-QXaLP5O-9mdIj0Wa8OT_cw0cHsuFvluMfgfRaRp0mTmoAvLK3LE_FPsTc3WJ98Slw7pU7gc14mjlt79rx_KjEnRgyjBe3oA9XZjNYxze3hAKUelrCaOU-DTj9fG4WUArviw"
]
froxy_token = "".join(token_parts)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request('https://api.shopier.com/v1/shop', headers={
    'Authorization': f'Bearer {froxy_token}',
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0'
})

try:
    with urllib.request.urlopen(req, context=ctx) as resp:
        print("Froxy Shopier Info:", resp.read().decode('utf-8'))
except Exception as e:
    print("Error:", e)
