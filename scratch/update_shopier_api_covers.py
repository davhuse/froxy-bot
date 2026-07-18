import urllib.request
import urllib.error
import json
import ssl
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

token_la = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5YjI5OWVmNzFlNTYyNDIzNDIxYTk5NDc1YzA2YWVlNiIsImp0aSI6IjBkZTEyZTUyN2E1Yjk2ZGJkNWQ3Yjk2M2ZiY2Q3ZjU1NzhkOGE4NDlmMTY5YTI2MTIzNzU5MWIzODYxYjk4MTFiNjhmYTcxZWMzYzkwNmRkZjBjYjMwY2IyOWJiZmQwMGY3OGJhNzA2ZmQ4Y2Q2ZDE1OWZjZjdjMTUwNmMxZGQ0NGIxNmMxYjU0MjY0YTdjMjFlY2M2MmZkM2ZlYmQ3NjciLCJpYXQiOjE3ODQxMjg1NjUsIm5iZiI6MTc4NDEyODU2NSwiZXhwIjoxOTQxOTEzMzI1LCJzdWIiOjI5ODgwNTAsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.XKdsT-LDfzF9OjHVffcay-AzQIA0vGAt3V0MJQMmaSK13awRUAeLu8Pm7cE_7IQlnjpx9-gvWlmv5K8FJriBQ8f656jS1idbCv96sFjSX-KcYKqqPJSEQQwYxJ-Helkkidy24r6X5dPTLx1a0Ps9w_VqLvwyJvNlFNOVEwHq-vYLiMIQ9kAyuBx1cQJ1zl0P-U2h9LXgYepoesHaWyavqSpRlOgDfbpjjfIaT3GfqmhA6gE553fJrCr-Ot0Z-OAy3t_VyWZlOAgiW10Jn-UPGxxmPgPLOE5PwYCHsEp9GSXf4A629evKL-k7f2k7i4ZpJrbqVUyxcNlCZThxUuyGog"
token_kv = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJiOGI0MjA0NWM1NDY2ZDdiMWQwODc0OGUzZTBkNDlmNSIsImp0aSI6IjllZDI4ZTU3ZjZkOTFjOWFjZTRjN2Y0YzNhZmUyZjg3YTg0NWEyZDAxNzdiNDgxZTlkNWE2OTAwZTY4YjVkYzliN2UxY2UwNmQ4YzYxZjQ3YTA2ZWJkOGEyMGJhMGNlMTM3ZDFjNDI0N2VhNGQzNzNhYzQ4YTFhYzBhZDIxOGM1YzVkZWM1ZGNiOTlkNjdlM2M5NTJjYjFjMWU5ZjlmZjMiLCJpYXQiOjE3ODQxMjIzODIsIm5iZiI6MTc4NDEyMjM4MiwiZXhwIjoxOTQxOTA3MTQyLCJzdWIiOjI1MDk0OTMsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.jdLI_JWWU1MlRz4A4vxKj0EtfeffmuJFzO8Eq3YC2aWiY1MFEZZ8x6HQdSiqdB3JY1U4Sirk8cVfysm1FU9ulCtrtcviPztPQWWGL0AGgbqRDlc2uw4YhuPzLIIafA_Ej1O_BIDI48UOK6LpvBWapMjISa23Jjj5MLISvYRH9lMS_v2IUDpjvsf-6H6Bpi1BCNvSlLoMRT8_SPnqPY3908zsm3xZvPfENBQAtpdvydAdFVtq-EaNesit5gWER8NaUickGDZ7_G7KOdF-08Ej4YOAxly_HvWaO8Gi_JzKqYnMgd66d-snGOpj0pIvsqKmRmdHJ53tflFF_X363dKaBg"

# 1. LisansArena updates
la_updates = {
    "49000910": "la_hbo.png",
    "49000911": "la_prime.png",
    "49000912": "la_prime.png",
    "48973854": "la_netflix_4k.png",
    "48973855": "la_youtube.png",
    "48973857": "la_spotify.png",
    "48973858": "la_canva.png",
    "48945472": "la_office365.png",
    "48945473": "la_windows_pro.png",
    "48945475": "la_steam_oyun.png",
    "48945476": "la_super_grok_1m.png",
    "48945480": "la_super_grok_3m.png",
    "48945481": "la_super_grok_6m.png",
    "48945482": "la_super_grok_12m.png",
    "48945484": "la_gamma_ultra.png",
    "48945485": "la_gamma_pro.png",
    "48945487": "la_gemini_ultra_davet.png",
    "48945489": "la_gemini_ultra_2500.png",
    "48945492": "la_gemini_pro_davet_12m.png",
    "48945493": "la_gemini_pro_hesap_12m.png",
    "48945669": "la_exxen.png",
    "48945671": "la_trendyol_yemek.png",
    "48945672": "la_trendyol_market.png",
    "48945675": "la_shell.png",
    "48901851": "lisansarena_crunchyroll_ortak.png",
    "48901852": "lisansarena_crunchyroll_ozel.png",
    "48901856": "lisansarena_grammarly_haftalik.png",
    "48901857": "lisansarena_grammarly_ortak.png",
    "48901858": "la_adobe_cc.png",
    "48901859": "la_adobe_cc.png",
    "48901869": "la_magnific_ai.png",
    "48901872": "lisansarena_scribd_ortak.png",
    "48901873": "lisansarena_scribd_kisisel.png",
    "48901874": "lisansarena_deepl_ortak.png",
    "48901875": "lisansarena_deepl_kisisel.png",
    "48901877": "la_perplexity_pro.png",
    "48901878": "lisansarena_telegram_account.png",
    "48901882": "la_xbox_gamepass.png",
    "48901888": "la_xbox_gamepass.png"
}

# 2. KeyVadi updates
kv_updates = {
    "47669159": "keyvadi_gemini_pro.png",
    "47669164": "keyvadi_gemini_pro.png",
    "47669192": "keyvadi_gemini_pro.png",
    "47669222": "keyvadi_gemini_pro.png",
    "47669248": "keyvadi_super_grok.png",
    "47669271": "keyvadi_super_grok.png",
    "47669295": "keyvadi_super_grok.png",
    "47669305": "keyvadi_super_grok.png",
    "47669310": "keyvadi_gamma.png",
    "47669316": "keyvadi_gamma.png",
    "47669321": "keyvadi_canva.png",
    "47669328": "keyvadi_adobe_cc.png",
    "47669341": "keyvadi_adobe_cc.png",
    "47669356": "keyvadi_adobe_cc.png",
    "47669362": "keyvadi_adobe_cc.png",
    "47669482": "keyvadi_trendyol_yemek.png",
    "47669486": "keyvadi_trendyol_market.png",
    "47669496": "keyvadi_shell.png",
    "48943133": "keyvadi_telegram_account.png",
    "48943136": "keyvadi_perplexity_pro.png",
    "48943137": "keyvadi_deepl_kisisel.png",
    "48943139": "keyvadi_deepl_ortak.png",
    "48943141": "keyvadi_scribd_kisisel.png",
    "48943143": "keyvadi_scribd_ortak.png",
    "48943144": "keyvadi_magnific_ai.png",
    "48943146": "keyvadi_crunchyroll_ozel.png",
    "48943148": "keyvadi_crunchyroll_ortak.png",
    "48943150": "keyvadi_grammarly_haftalik.png",
    "48943151": "keyvadi_grammarly_ortak.png"
}

def update_store_covers(token, updates_dict, store_name):
    print(f"\n--- Updating images on {store_name} Shopier Store ---")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    for idx, (pid, filename) in enumerate(updates_dict.items()):
        url = f"https://api.shopier.com/v1/products/{pid}"
        payload = {
            "media": [
                {
                    "type": "image",
                    "url": f"https://veridia-bot.onrender.com/static/{filename}",
                    "placement": 1
                }
            ]
        }
        
        print(f"[{idx+1}/{len(updates_dict)}] ID {pid} -> {filename}...")
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="PUT")
        try:
            with urllib.request.urlopen(req, context=ctx) as r:
                print("  [SUCCESS]")
        except urllib.error.HTTPError as e:
            print(f"  [FAILED] HTTP Error {e.code}: {e.reason}")
        except Exception as e:
            print(f"  [FAILED] Error: {e}")
        time.sleep(1.5)

# 1. Update LisansArena
update_store_covers(token_la, la_updates, "LISANSARENA")

# 2. Update KeyVadi (disabled since old products belong to the old account)
# update_store_covers(token_kv, kv_updates, "KEYVADI")

print("\nDone updating all Shopier covers!")
