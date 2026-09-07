import urllib.request
import json

api_key = "rnd_coICmwUZglrHzzHC84glOBZTgl1U"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

svc_id = "srv-daem9k1t0dsc73ar02dg"

try:
    req = urllib.request.Request(f"https://api.render.com/v1/services/{svc_id}/env-vars", headers=headers)
    with urllib.request.urlopen(req) as resp:
        env_vars = json.loads(resp.read().decode('utf-8'))
        print("=== RENDER ENV VARS ===")
        for item in env_vars:
            ev = item.get("envVar", {})
            key = ev.get("key")
            val = ev.get("value", "")
            # Mask sensitive tokens
            masked = val[:6] + "..." + val[-4:] if len(val) > 10 else "***"
            print(f" {key} = {masked}")
except Exception as e:
    print("Error:", e)
