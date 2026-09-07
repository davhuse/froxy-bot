import urllib.request
import json

tokens = [
    '8961373302:AAGNs9fcPFU_XcWDUlhbNhQ2hRNzyRu6_MI',
    '8845484139:AAE7NeZdo4kSurKMNFctA08GhMQrbSQPvjg',
    '8712009642:AAE2jKKUwjhVpRC38dpFQkbSt2srjdUDuuc',
    '8272543860:AAGESmDOiIXFoK7FYCh0UfP3IplBcvMhTEA'
]

for t in set(tokens):
    try:
        req = urllib.request.Request(f'https://api.telegram.org/bot{t}/getMe')
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            res = data.get('result', {})
            print(f"Token: {t[:15]}... -> @{res.get('username')} ({res.get('first_name')})")
    except Exception as e:
        print(f"Token: {t[:15]}... -> Error: {e}")
