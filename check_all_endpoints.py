import urllib.request
import json
import ssl
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = "https://froxy-bot-kgky.onrender.com"
endpoints = [
    "/health",
    "/froxy/api/models",
    "/froxy/api/image-models",
    "/froxy/api/products",
    "/keyvadi/api/products",
]

for ep in endpoints:
    url = f"{base}{ep}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            code = r.status
            content = r.read().decode("utf-8")
            print(f"[OK] {ep} -> HTTP {code} (len: {len(content)})")
    except urllib.error.HTTPError as e:
        print(f"[ERR] {ep} -> HTTP {e.code}")
    except Exception as e:
        print(f"[ERR] {ep} -> Error: {e}")
