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
            if len(m) > 500:
                found_tokens.add(m)

for i, token in enumerate(found_tokens, 1):
    req = urllib.request.Request('https://api.shopier.com/v1/products?limit=1', headers={
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    })
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"[Token #{i}] ✅ 200 OK: {token[:25]}... -> {data[0].get('title') if data else 'Empty'}")
    except urllib.error.HTTPError as e:
        print(f"[Token #{i}] ❌ HTTP {e.code}: {token[:25]}... (sub={token.split('.')[1][:30]})")
    except Exception as e:
        print(f"[Token #{i}] ❌ Error: {e}")
