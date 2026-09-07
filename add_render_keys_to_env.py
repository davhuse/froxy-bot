import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

api_key = "rnd_coICmwUZglrHzzHC84glOBZTgl1U"
svc_id = "srv-daem9k1t0dsc73ar02dg"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# 1. Fetch current env vars on Render
req = urllib.request.Request(f"https://api.render.com/v1/services/{svc_id}/env-vars", headers=headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    current_vars = json.loads(resp.read().decode('utf-8'))

merged_env = {}
for item in current_vars:
    ev = item.get("envVar", {})
    k = ev.get("key")
    v = ev.get("value")
    if k and v:
        merged_env[k] = v

merged_env["RENDER_API_KEY"] = api_key
merged_env["RENDER_SERVICE_ID"] = svc_id

new_env_list = [{"key": k, "value": v} for k, v in merged_env.items()]

put_req = urllib.request.Request(
    f"https://api.render.com/v1/services/{svc_id}/env-vars",
    data=json.dumps(new_env_list).encode('utf-8'),
    headers=headers,
    method="PUT"
)

with urllib.request.urlopen(put_req, context=ctx) as resp:
    result = json.loads(resp.read().decode('utf-8'))
    print("SUCCESS! Render environment variables now include RENDER_API_KEY and RENDER_SERVICE_ID! Total:", len(result))
