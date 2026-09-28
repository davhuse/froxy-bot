import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
PROJECT_ID = '5fa77867-f818-4da3-b9d9-702529879e6f'
ENV_ID = '6ea40a3d-d7cc-4675-a593-29f6db038de1'
SVC_ID = '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = """
query GetVars($projId: String!, $envId: String!, $svcId: String!) {
  variables(projectId: $projId, environmentId: $envId, serviceId: $svcId)
}
"""

r = requests.post(url, json={'query': q, 'variables': {'projId': PROJECT_ID, 'envId': ENV_ID, 'svcId': SVC_ID}}, headers=headers)
vars_data = r.json().get('data', {}).get('variables', {})
bot_cfg_str = vars_data.get('BOT_CONFIG_JSON', '{}')
try:
    bot_cfg = json.loads(bot_cfg_str)
    print("admin_id in BOT_CONFIG_JSON:", bot_cfg.get("admin_id"))
    print("support_chat_id in BOT_CONFIG_JSON:", bot_cfg.get("support_chat_id"))
except Exception as e:
    print("JSON error:", e)
print("TELEGRAM_ADMIN_ID var:", vars_data.get("TELEGRAM_ADMIN_ID"))
