import json
import re
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\fbd09d2b-4007-40b6-be24-bbd2f7ab73dc\.system_generated\logs\transcript_full.jsonl"

found_tokens = set()
with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        matches = re.findall(r'eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}', line)
        for m in matches:
            if len(m) > 500: # JWT Shopier tokens are ~1000 chars
                found_tokens.add(m)

print(f"Testing {len(found_tokens)} unique tokens against Shopier API...")

for i, token in enumerate(found_tokens, 1):
    req = urllib.request.Request('https://api.shopier.com/v1/products?limit=2', headers={
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    })
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"\n[Token #{i}] ✅ VALID SHOPIER TOKEN!")
            print(f"Token: {token}")
            if data and len(data) > 0:
                print("First product title:", data[0].get("title"))
                print("First product url:", data[0].get("url"))
            else:
                print("Store has 0 products.")
    except urllib.error.HTTPError as e:
        # print(f"[Token #{i}] ❌ HTTP {e.code}")
        pass
    except Exception as e:
        # print(f"[Token #{i}] ❌ Error: {e}")
        pass
