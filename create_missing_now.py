import requests
import json
import os
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

token_kv = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJiOGI0MjA0NWM1NDY2ZDdiMWQwODc0OGUzZTBkNDlmNSIsImp0aSI6IjllZDI4ZTU3ZjZkOTFjOWFjZTRjN2Y0YzNhZmUyZjg3YTg0NWEyZDAxNzdiNDgxZTlkNWE2OTAwZTY4YjVkYzliN2UxY2UwNmQ4YzYxZjQ3YTA2ZWJkOGEyMGJhMGNlMTM3ZDFjNDI0N2VhNGQzNzNhYzQ4YTFhYzBhZDIxOGM1YzVkZWM1ZGNiOTlkNjdlM2M5NTJjYjFjMWU5ZjlmZjMiLCJpYXQiOjE3ODQxMjIzODIsIm5iZiI6MTc4NDEyMjM4MiwiZXhwIjoxOTQxOTA3MTQyLCJzdWIiOjI1MDk0OTMsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.jdLI_JWWU1MlRz4A4vxKj0EtfeffmuJFzO8Eq3YC2aWiY1MFEZZ8x6HQdSiqdB3JY1U4Sirk8cVfysm1FU9ulCtrtcviPztPQWWGL0AGgbqRDlc2uw4YhuPzLIIafA_Ej1O_BIDI48UOK6LpvBWapMjISa23Jjj5MLISvYRH9lMS_v2IUDpjvsf-6H6Bpi1BCNvSlLoMRT8_SPnqPY3908zsm3xZvPfENBQAtpdvydAdFVtq-EaNesit5gWER8NaUickGDZ7_G7KOdF-08Ej4YOAxly_HvWaO8Gi_JzKqYnMgd66d-snGOpj0pIvsqKmRmdHJ53tflFF_X363dKaBg'
token_la = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5YjI5OWVmNzFlNTYyNDIzNDIxYTk5NDc1YzA2YWVlNiIsImp0aSI6IjBkZTEyZTUyN2E1Yjk2ZGJkNWQ3Yjk2M2ZiY2Q3ZjU1NzhkOGE4NDlmMTY5YTI2MTIzNzU5MWIzODYxYjk4MTFiNjhmYTcxZWMzYzkwNmRkZjBjYjMwY2IyOWJiZmQwMGY3OGJhNzA2ZmQ4Y2Q2ZDE1OWZjZjdjMTUwNmMxZGQ0NGIxNmMxYjU0MjY0YTdjMjFlY2M2MmZkM2ZlYmQ3NjciLCJpYXQiOjE3ODQxMjg1NjUsIm5iZiI6MTc4NDEyODU2NSwiZXhwIjoxOTQxOTEzMzI1LCJzdWIiOjI5ODgwNTAsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.XKdsT-LDfzF9OjHVffcay-AzQIA0vGAt3V0MJQMmaSK13awRUAeLu8Pm7cE_7IQlnjpx9-gvWlmv5K8FJriBQ8f656jS1idbCv96sFjSX-KcYKqqPJSEQQwYxJ-Helkkidy24r6X5dPTLx1a0Ps9w_VqLvwyJvNlFNOVEwHq-vYLiMIQ9kAyuBx1cQJ1zl0P-U2h9LXgYepoesHaWyavqSpRlOgDfbpjjfIaT3GfqmhA6gE553fJrCr-Ot0Z-OAy3t_VyWZlOAgiW10Jn-UPGxxmPgPLOE5PwYCHsEp9GSXf4A629evKL-k7f2k7i4ZpJrbqVUyxcNlCZThxUuyGog'

def upload_uguu(filepath):
    print(f"Uploading {filepath}...")
    with open(filepath, 'rb') as f:
        r = requests.post('https://uguu.se/upload.php', files={'files[]': f})
        if r.status_code == 200:
            try:
                url = r.json()['files'][0]['url']
                print(f"Uploaded to {url}")
                return url
            except Exception as e:
                pass
    return None

def create_product(token, name, price, desc, img_url):
    url = "https://api.shopier.com/v1/products"
    payload = {
        "title": name,
        "description": desc,
        "type": "digital",
        "media": [{"type": "image", "url": img_url, "placement": 1}],
        "priceData": {
            "currency": "TRY",
            "price": f"{price:.2f}",
            "discount": False,
            "discountedPrice": f"{price:.2f}",
            "shippingPrice": "0.00"
        },
        "stockQuantity": 999,
        "shippingPayer": "sellerPays"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            res_data = json.loads(r.read().decode("utf-8"))
            print(f"[SUCCESS] Product ID: {res_data.get('id')} | URL: {res_data.get('url')}")
            return res_data.get("url")
    except urllib.error.HTTPError as e:
        print(f"[FAILED] HTTP {e.code}: {e.read().decode('utf-8')}")
        return None

new_products = [
    # Steam Random was successfully uploaded to KeyVadi in the previous run (ID 49099001). 
    # But since we didn't save the URL to bot_config, we'll recreate it (or just recreate everything, we can delete duplicates later).
    {"name": "Steam 200 Dolar Random Key", "price": 30.00, "slug": "steam_random", "desc": "Steam platformunda gecerli random key. Aninda teslimat.", "img_kv": "keyvadi_steam_random.png", "img_la": "lisansarena_steam_random.png"},
    {"name": "Netflix 4K UHD Ortak Profil", "price": 39.99, "slug": "netflix_4k", "desc": "Kisisel Netflix 4K Ultra HD Profili. Ortak hesapta size ait ozel profil.", "img_kv": "keyvadi_netflix_4k.png", "img_la": "lisansarena_netflix_4k.png"},
    {"name": "Zula Random Hesap", "price": 5.00, "slug": "zula_random", "desc": "En az 0, en cok 250 skin cikmaktadir.\nEn az 1, en cok 155 level cikmaktadir.\nHesaplarda minumum 1000-3000 Zula altini cikmaktadir.\nYeni acilmis hesap cikma ihtimali vardir.\nAktif olmasak bile satin alim islemi gerceklestirebilirsiniz. Otomatik teslimattir.\nHer hesap tek bir kisiye satilir.", "img_kv": "keyvadi_zula_random.png", "img_la": "lisansarena_zula_random.png"},
    {"name": "FC26 + Online Her Seyi Degisen Hesap", "price": 299.99, "slug": "fc26_hesap", "desc": "FC26 ve Online dahil her seyi degisen Steam hesabi. Aninda teslim.", "img_kv": "keyvadi_fc26_hesap.png", "img_la": "lisansarena_fc26_hesap.png"}
]

with open("bot_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

print("--- KEYVADI PRODUCTS ---")
for p in new_products:
    img_path = os.path.join("static", p["img_kv"])
    img_url = upload_uguu(img_path)
    if img_url:
        shopier_url = create_product(token_kv, p["name"], p["price"], p["desc"], img_url)
        if shopier_url:
            # Keyvadi slugs just use the slug name
            config["shopier_links"][p["slug"]] = shopier_url

print("\n--- LISANSARENA PRODUCTS ---")
for p in new_products:
    img_path = os.path.join("static", p["img_la"])
    img_url = upload_uguu(img_path)
    if img_url:
        shopier_url = create_product(token_la, p["name"], p["price"], p["desc"], img_url)
        if shopier_url:
            # Lisansarena uses specific lisansarena_slug names? Let's check how they are referenced in the bot.
            # Usually we can store them as la_slug in the same dict or the bot handles it.
            # Let's save it as lisansarena_{slug} for LisansArena links.
            config["shopier_links"][f"lisansarena_{p['slug']}"] = shopier_url

with open("bot_config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, indent=4)

print("Done! bot_config.json updated.")
