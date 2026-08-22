import urllib.request
import json
import ssl
import os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def upload_image_tmpfiles(filepath):
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    with open(filepath, 'rb') as f:
        img_bytes = f.read()

    filename = os.path.basename(filepath)
    body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f'Content-Type: image/png\r\n\r\n'
    ).encode('utf-8') + img_bytes + f'\r\n--{boundary}--\r\n'.encode('utf-8')

    req = urllib.request.Request('https://tmpfiles.org/api/v1/upload', data=body, headers={
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'User-Agent': 'Mozilla/5.0'
    })
    with urllib.request.urlopen(req, context=ctx) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        page_url = res.get('data', {}).get('url', '')
        return page_url.replace('tmpfiles.org/', 'tmpfiles.org/dl/')

cdn_url = upload_image_tmpfiles('keyvadi_banner.png')
print('CDN URL:', cdn_url)

token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJiOGI0MjA0NWM1NDY2ZDdiMWQwODc0OGUzZTBkNDlmNSIsImp0aSI6ImY1YmQ1Yzk4Y2U3NmEwNWIyNDhiYTNmY2Q3MThjN2YzNjgwNzE2Y2M4ODhkNWM5ZWZjNzIzNmY0MDA3YmZiNjA1MmEwOTlmYWJlZWY5Y2I0NzgxMjY4OWI4YWM0NTI3MmE4NmNmZGNkMjU0YTJjNThjYTdhMzc0MjNhMjE5ZGQzNjNhM2FjMmM3YTFhZTFiZTY4OWRmODI1MmUzMDE0MjMiLCJpYXQiOjE3ODU1MjA4MDUsIm5iZiI6MTc4NTUyMDgwNSwiZXhwIjoxOTQzMzA1NTY1LCJzdWIiOjI1MDk0OTMsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.MjmL2Y8Eapk8FYETmZbcdo0sYqAseKPu1I0qGKiMOHCYrlKqWsC53IOnzf8WiZEeUvHAFDxqmqmEGuo5x_Xx6ncMX_8sj0VXzkaEOl5EnGjeq3qbwkGOhXxUT7d914qMTELeku0AysnPQdOiGgot-pSh2XMl86YEtTJmLD1qjQd9uG5VPbzcjcHxYUf18WZ6beZf7974xAo-36rJK2F0nZ1JvWaGZz-lG0XyEGh50HQIyBPwSkCb85pJEKbPa_n-iTR5D1eMwQyGkWMT2IpHQ8PHtUaDIK-S5UNTlWEPLxUDYQevnJ13ajGjpXVVXONURCYD2WbtCvWciGWyNqyJ8Q'

payload = {
    'title': 'KeyVadi Cüzdan Yükleme (₺50.00) - ID:8797763469',
    'type': 'digital',
    'description': 'KeyVadi Telegram Mini App Otomatik Bakiye Yükleme. Müşteri ID: 8797763469',
    'priceData': {
        'currency': 'TRY',
        'price': '50.00',
        'discount': False,
        'discountedPrice': '50.00',
        'shippingPrice': '0.00'
    },
    'stockQuantity': 999,
    'shippingPayer': 'sellerPays',
    'media': [
        {
            'type': 'image',
            'url': cdn_url,
            'placement': 1
        }
    ]
}

req = urllib.request.Request(
    'https://api.shopier.com/v1/products',
    data=json.dumps(payload).encode('utf-8'),
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }
)

with urllib.request.urlopen(req, context=ctx) as resp:
    body = resp.read().decode('utf-8')
    data = json.loads(body)
    pid = data.get('id')
    print('SUCCESSFULLY CREATED LIVE SHOPIER PRODUCT ID:', pid)
    print('DIRECT SHOPIER PAYMENT LINK: https://www.shopier.com/keyvadi/' + str(pid))
