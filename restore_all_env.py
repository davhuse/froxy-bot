import urllib.request
import json
import os
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

api_key = "rnd_coICmwUZglrHzzHC84glOBZTgl1U"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

svc_id = "srv-daem9k1t0dsc73ar02dg"

# Fetch with limit=100
req = urllib.request.Request(f"https://api.render.com/v1/services/{svc_id}/env-vars?limit=100", headers=headers)
with urllib.request.urlopen(req) as resp:
    current_vars = json.loads(resp.read().decode('utf-8'))

merged_env = {}
for item in current_vars:
    ev = item.get("envVar", {})
    k = ev.get("key")
    v = ev.get("value")
    if k and v:
        merged_env[k] = v

with open("keyvadi_session_output.txt", "r", encoding="utf-8") as f:
    keyvadi_sess = f.read().strip()

with open("session_lisansarena_new.txt", "r", encoding="utf-8") as f:
    la_sess = f.read().strip()

core_vars = {
    "RENDER_API_KEY": api_key,
    "RENDER_SERVICE_ID": svc_id,
    "AD_STRING_SESSION_KEYVADI": keyvadi_sess,
    "AD_STRING_SESSION_LISANSARENA": la_sess,
    "FIREBASE_API_KEY": "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo",
    "FIREBASE_PROJECT_ID": "bot-2-63772",
    "KEYVADI_SUPPORT_BOT_TOKEN": "8712009642:AAE2jKKUwjhVpRC38dpFQkbSt2srjdUDuuc",
    "LISANSARENA_BOT_TOKEN": "8272543860:AAGESmDOiIXFoK7FYCh0UfP3IplBcvMhTEA",
    "FROXY_SUPPORT_BOT_TOKEN": "8845484139:AAE7NeZdo4kSurKMNFctA08GhMQrbSQPvjg",
    "BOT_RUNTIME_ENABLED": "true",
    "BOT_AD_ENABLED": "true",
    "BOT_RUNTIME_OWNER": "render",
    "PANEL_ADMIN_TOKEN": "VOJVbVkVHQBw5J3zI8vQeW2zP5iK6uY9",
    "TELEGRAM_API_ID": "31076280",
    "TELEGRAM_API_HASH": "7ba4072dcf0a05a7ccf80e570866b6d8",
    "TELEGRAM_ADMIN_ID": "6196006704",
    "FLASK_SECRET_KEY": "NmWPrtFkZTQpWsL7xRvY8uBcDeF9gHiJ1kLmNoP3qRsTuVwXyZ2aBcDeFgHiEf8e",
    "LISANSARENA_DATABASE_URL": "postgresql://neondb_owner:npg_uP0xI6rYwWve@ep-bitter-dust-a2i29e9t.eu-central-1.aws.neon.tech/neondb?sslmode=require",
    "LISANSARENA_STOCK_KEY": "YxxyFpEfnYh7mXf4kXW5b3pL9kM2nQ8vRtY1uZaX8Pk",
    "LISANSARENA_SHOPIER_WEBHOOK_SECRET": "5889af8465c40026e03328ceca21ebaa7951a37c955ce773b0631ba95c525529",
    "SHOPIER_KEYVADI_ACCESS_TOKEN": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJiOGI0MjA0NWM1NDY2ZDdiMWQwODc0OGUzZTBkNDlmNSIsImp0aSI6ImY1YmQ1Yzk4Y2U3NmEwNWIyNDhiYTNmY2Q3MThjN2YzNjgwNzE2Y2M4ODhkNWM5ZWZjNzIzNmY0MDA3YmZiNjA1MmEwOTlmYWJlZWY5Y2I0NzgxMjY4OWI4YWM0NTI3MmE4NmNmZGNkMjU0YTJjNThjYTdhMzc0MjNhMjE5ZGQzNjNhM2FjMmM3YTFhZTFiZTY4OWRmODI1MmUzMDE0MjMiLCJpYXQiOjE3ODU1MjA4MDUsIm5iZiI6MTc4NTUyMDgwNSwiZXhwIjoxOTQzMzA1NTY1LCJzdWIiOjI1MDk0OTMsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.MjmL2Y8Eapk8FYETmZbcdo0sYqAseKPu1I0qGKiMOHCYrlKqWsC53IOnzf8WiZEeUvHAFDxqmqmEGuo5x_Xx6ncMX_8sj0VXzkaEOl5EnGjeq3qbwkGOhXxUT7d914qMTELeku0AysnPQdOiGgot-pSh2XMl86YEtTJmLD1qjQd9uG5VPbzcjcHxYUf18WZ6beZf7974xAo-36rJK2F0nZ1JvWaGZz-lG0XyEGh50HQIyBPwSkCb85pJEKbPa_n-iTR5D1eMwQyGkWMT2IpHQ8PHtUaDIK-S5UNTlWEPLxUDYQevnJ13ajGjpXVVXONURCYD2WbtCvWciGWyNqyJ8Q",
    "SHOPIER_LISANSARENA_ACCESS_TOKEN": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5YjI5OWVmNzFlNTYyNDIzNDIxYTk5NDc1YzA2YWVlNiIsImp0aSI6Ijg2NGI3ZTdkY2Y5NzlmMTIzMThkMTI5YjFjNjJhOTg4ODAyNTYyYTE2N2VjMjlmM2RmZDk2NmI2YWNjOTdkNzFmY2M3OTQxM2E5ZTJjMDU5ZTNmY2UwODYxOWJjMjNjZDU1MmU5ZjI5MzI2MDhmNjQxOTg0YjZmZjdhNWU4ZGY5MjE4M2MzNWQ2OTljMDY2NDMzYzA0NGJhNWU4MWY1ZmUiLCJpYXQiOjE3ODY2NDEzNDgsIm5iZiI6MTc4NjY0MTM0OCwiZXhwIjoxOTQ0NDI2MTA4LCJzdWIiOjI5ODgwNTAsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.E9lMtLx7ms1_8Mid7KHpZvYXT7PH3T4qxkoBLsB8vptV8RLipObYmBUM2LPsLnxybpWUOMxtmffQNY2pPxtM6stRWrkooYd7kLuycBWpRwHPRaE2PLchwUjHl3jtLKTDsj74UoyRnQPZwf6y7th6QRMcD6SD7YLPkz5tkBGndbRrgcLcwcG-xcYglKfVGV6bECq47BxcANb1MBOOCOCFHXwcwnwqbVLlD7IQWDSMtfFl_5U9nV8iY9R7447VLtPb55PMMhv086Mi6ucBPk-DcOSwwrGbMypgjax8HIrq-giDvV0FOClhVOMxJjIkg6oE9RM85WgDM1FLfzBDNPyN4g",
    "SHOPIER_FROXY_ACCESS_TOKEN": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJmOTMzYTA0MDk0ZmZhZjU0MTBkMmU3Y2UxNzk5NTQ4MCIsImp0aSI6Ijc4MmU4ODcxZWJjN2Y0MDZjM2M5ZjhjNmM0ZWYzNzYxZGY0MTI1YjljZjI0NDc0MTZhMWE1MTJiMmNiYjRhZGZlNjI5YTZiNjc2NDI3ZmE1NDE3MDk1MTM5NTNhYjM1NDIwMDRjZDg1YTM3YzZiZDM5MTg0NjEyZDA3NWFhY2Y3ZDM5YzM4OWM2OTMzMDRkYjZlMzI4NmQ3NzU3NGUyNDMiLCJpYXQiOjE3ODgzMDM0MTAsIm5iZiI6MTc4ODMwMzQxMCwiZXhwIjoxOTQ2MDg4MTcwLCJzdWIiOjI5NDM0ODgsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.uTicrPhDBrpXdMSnLRlAIfsegUSl3WkJPYxpWf3W2QC_dDXQajpA6Rmw7x7ySRJo958vSADGKoSDX700Vx9AvUumbOQRRa20ZwJ5UIyqUkc_M_yOGYGCszug9RDEMwEpS_va3tQM4cU3LPOPkC53APwjGRhQRanrw-8RfZBsaUrGidJgRdLY-G0gJk6f5Tq7_3NfPPuq-CCS8l6PXwm2GsM74Pp7SNJLmUz1vG3VY0JXjzah4reC_RxjfRziHK5diweU3-Nmn7iEoyI2Bp-Itfpq0t_27ECjIaxWBom18DUmaMbPkU-8tdqS9YONQUtZ6H-jRJcMzeVPlI7rVaN-9w"
}

for k, v in core_vars.items():
    merged_env[k] = v

new_env_list = [{"key": k, "value": v} for k, v in merged_env.items()]

put_req = urllib.request.Request(
    f"https://api.render.com/v1/services/{svc_id}/env-vars",
    data=json.dumps(new_env_list).encode('utf-8'),
    headers=headers,
    method="PUT"
)

with urllib.request.urlopen(put_req) as resp:
    result = json.loads(resp.read().decode('utf-8'))
    print("SUCCESS! Render environment variables restored. Total variables:", len(result))
