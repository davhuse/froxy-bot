import urllib.request
import json
import sys

base_url = 'https://froxy-bot-kgky.onrender.com'

# Test Shopier balance creation endpoint for KeyVadi
try:
    req = urllib.request.Request(
        f'{base_url}/api/balance/create-dynamic-topup',
        data=json.dumps({'amount': 50.0}).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req) as resp:
        print('KeyVadi topup response:', resp.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print('KeyVadi topup error:', e.code, e.read().decode('utf-8'))
except Exception as e:
    print('KeyVadi topup exception:', e)
