import json
import urllib.request

with open('extracted_all_render_envs.json', 'r', encoding='utf-8') as f:
    envs = json.load(f)

current = envs['froxy-bot-1 (CURRENT)']
zzbu = envs['froxy-bot-live (ZZBu)']

target_env = dict(current)
# Working bot tokens
target_env['KEYVADI_SUPPORT_BOT_TOKEN'] = zzbu['KEYVADI_SUPPORT_BOT_TOKEN']
target_env['KEYVADI_BOT_TOKEN'] = zzbu['KEYVADI_SUPPORT_BOT_TOKEN']
target_env['FROXY_SUPPORT_BOT_TOKEN'] = zzbu['FROXY_BOT_TOKEN']
target_env['FROXY_BOT_TOKEN'] = zzbu['FROXY_BOT_TOKEN']
target_env['LISANSARENA_BOT_TOKEN'] = zzbu['LISANSARENA_BOT_TOKEN']
target_env['LISANSARENA_SUPPORT_BOT_TOKEN'] = zzbu['LISANSARENA_BOT_TOKEN']

# Working KeyVadi string session
target_env['AD_STRING_SESSION_KEYVADI'] = zzbu['AD_STRING_SESSION_KEYVADI']

# AI keys
if 'GROQ_API_KEY' in zzbu:
    target_env['GROQ_API_KEY'] = zzbu['GROQ_API_KEY']
if 'FREEMODEL_API_KEY' in zzbu:
    target_env['FREEMODEL_API_KEY'] = zzbu['FREEMODEL_API_KEY']

payload = [{"key": k, "value": v} for k, v in target_env.items()]

render_key = 'rnd_4c83vU85zEZ7KOjaS5crYqM4x55G'
srv_id = 'srv-danfkkek1f9s738iq5rg'

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
    print(f"Successfully applied {len(res)} env vars to {srv_id}!")

# Trigger deploy
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
