import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://raw.githubusercontent.com/davhuse/froxy-bot/main/static/keyvadi_perplexity_pro.png"
print("Testing raw GitHub URL:", url)
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx) as r:
        print("Success! Content length:", len(r.read()))
except Exception as e:
    print("Failed to fetch raw GitHub URL:", e)
