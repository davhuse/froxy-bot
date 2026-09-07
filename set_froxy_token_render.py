import urllib.request
import json

api_key = "rnd_coICmwUZglrHzzHC84glOBZTgl1U"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

svc_id = "srv-daem9k1t0dsc73ar02dg"

froxy_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJmOTMzYTA0MDk0ZmZhZjU0MTBkMmU3Y2UxNzk5NTQ4MCIsImp0aSI6Ijc4MmU4ODcxZWJjN2Y0MDZjM2M5ZjhjNmM0ZWYzNzYxZGY0MTI1YjljZjI0NDc0MTZhMWE1MTJiMmNiYjRhZGZlNjI5YTZiNjc2NDI3ZmE1NDE3MDk1MTM5NTNhYjM1NDIwMDRjZDg1YTM3YzZiZDM5MTg0NjEyZDA3NWFhY2Y3ZDM5YzM4OWM2OTMzMDRkYjZlMzI4NmQ3NzU3NGUyNDMiLCJpYXQiOjE3ODgzMDM0MTAsIm5iZiI6MTc4ODMwMzQxMCwiZXhwIjoxOTQ2MDg4MTcwLCJzdWIiOjI5NDM0ODgsInNjb3BlcyI6WyJvcmRlcnM6cmVhZCIsIm9yZGVyczp3cml0ZSIsInByb2R1Y3RzOnJlYWQiLCJwcm9kdWN0czp3cml0ZSIsInNoaXBwaW5nczpyZWFkIiwic2hpcHBpbmdzOndyaXRlIiwiZGlzY291bnRzOnJlYWQiLCJkaXNjb3VudHM6d3JpdGUiLCJwYXlvdXRzOnJlYWQiLCJyZWZ1bmRzOnJlYWQiLCJyZWZ1bmRzOndyaXRlIiwic2hvcDpyZWFkIiwic2hvcDp3cml0ZSJdfQ.uTicrPhDBrpXdMSnLRlAIfsegUSl3WkJPYxpWf3W2QC_dDXQajpA6Rmw7x7ySRJo958vSADGKoSDX700Vx9AvUumbOQRRa20ZwJ5UIyqUkc_M_yOGYGCszug9RDEMwEpS_va3tQM4cU3LPOPkC53APwjGRhQRanrw-8RfZBsaUrGidJgRdLY-G0gJk6f5Tq7_3NfPPuq-CCS8l6PXwm2GsM74Pp7SNJLmUz1vG3VY0JXjzah4reC_RxjfRziHK5diweU3-Nmn7iEoyI2Bp-Itfpq0t_27ECjIaxWBom18DUmaMbPkU-8tdqS9YONQUtZ6H-jRJcMzeVPlI7rVaN-9w"

# 1. Fetch current env vars
req = urllib.request.Request(f"https://api.render.com/v1/services/{svc_id}/env-vars", headers=headers)
with urllib.request.urlopen(req) as resp:
    current_vars = json.loads(resp.read().decode('utf-8'))

# Convert to list of {key, value}
new_env = []
found = False
for item in current_vars:
    ev = item.get("envVar", {})
    k = ev.get("key")
    v = ev.get("value")
    if k == "SHOPIER_FROXY_ACCESS_TOKEN":
        new_env.append({"key": k, "value": froxy_token})
        found = True
    else:
        new_env.append({"key": k, "value": v})

if not found:
    new_env.append({"key": "SHOPIER_FROXY_ACCESS_TOKEN", "value": froxy_token})

# 2. Update env vars via PUT
put_req = urllib.request.Request(
    f"https://api.render.com/v1/services/{svc_id}/env-vars",
    data=json.dumps(new_env).encode('utf-8'),
    headers=headers,
    method="PUT"
)

try:
    with urllib.request.urlopen(put_req) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        print("Successfully updated Render environment variables!")
        print("Total env vars:", len(result))
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
