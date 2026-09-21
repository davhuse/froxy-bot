import urllib.request
import json
import time

render_key = 'rnd_4c83vU85zEZ7KOjaS5crYqM4x55G'
srv_id = 'srv-danfkkek1f9s738iq5rg'

# Current envs on render
req = urllib.request.Request(f'https://api.render.com/v1/services/{srv_id}/env-vars', headers={'Authorization': f'Bearer {render_key}'})
with urllib.request.urlopen(req) as resp:
    curr_data = json.loads(resp.read().decode())
    curr_map = {item['envVar']['key']: item['envVar']['value'] for item in curr_data}

# Backup envs
with open('extracted_all_render_envs.json', 'r', encoding='utf-8') as f:
    saved = json.load(f)

zzbu = saved['froxy-bot-live (ZZBu)']

merged = dict(curr_map)
# Add missing sessions
merged['AD_STRING_SESSION_FROXY'] = zzbu['AD_STRING_SESSION_FROXY']
merged['AD_STRING_SESSION_KEYVADI'] = zzbu['AD_STRING_SESSION_KEYVADI']
merged['AD_STRING_SESSION_LISANSARENA'] = zzbu['AD_STRING_SESSION_LISANSARENA']

# Add missing shopier
merged['SHOPIER_KEYVADI_ACCESS_TOKEN'] = saved['froxy-bot-1 (CURRENT)']['SHOPIER_KEYVADI_ACCESS_TOKEN']
merged['SHOPIER_LISANSARENA_ACCESS_TOKEN'] = saved['froxy-bot-1 (CURRENT)']['SHOPIER_LISANSARENA_ACCESS_TOKEN']
merged['SHOPIER_FROXY_ACCESS_TOKEN'] = saved['froxy-bot-1 (CURRENT)']['SHOPIER_FROXY_ACCESS_TOKEN']

# Add missing AI keys
if 'GROQ_API_KEY' in zzbu:
    merged['GROQ_API_KEY'] = zzbu['GROQ_API_KEY']
if 'FREEMODEL_API_KEY' in zzbu:
    merged['FREEMODEL_API_KEY'] = zzbu['FREEMODEL_API_KEY']

# Add bot tokens if missing
merged['FROXY_BOT_TOKEN'] = zzbu['FROXY_BOT_TOKEN']
merged['LISANSARENA_SUPPORT_BOT_TOKEN'] = zzbu['LISANSARENA_BOT_TOKEN']
merged['DISABLE_LISANSARENA_AD'] = 'false'

payload = [{"key": k, "value": v} for k, v in merged.items()]

req = urllib.request.Request(
    f'https://api.render.com/v1/services/{srv_id}/env-vars',
    data=json.dumps(payload).encode('utf-8'),
    headers={
        'Authorization': f'Bearer {render_key}',
        'Content-Type': 'application/json'
    },
    method='PUT'
)

with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode())
    print(f"Successfully pushed {len(res)} env vars to {srv_id}!")

# Deploy service with fresh cache
deploy_req = urllib.request.Request(
    f'https://api.render.com/v1/services/{srv_id}/deploys',
    data=json.dumps({"clearCache": "do_not_clear"}).encode('utf-8'),
    headers={
        'Authorization': f'Bearer {render_key}',
        'Content-Type': 'application/json'
    },
    method='POST'
)
with urllib.request.urlopen(deploy_req) as resp:
    deploy_res = json.loads(resp.read().decode())
    print(f"Triggered deploy: {deploy_res.get('id')} (status: {deploy_res.get('status')})")
