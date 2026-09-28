import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
PROJECT_ID = '5fa77867-f818-4da3-b9d9-702529879e6f'
ENV_ID = '6ea40a3d-d7cc-4675-a593-29f6db038de1'
SVC_ID = '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'

url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = '''
query GetVars($projectId: String!, $environmentId: String!, $serviceId: String!) {
  variables(projectId: $projectId, environmentId: $environmentId, serviceId: $serviceId)
}
'''

r = requests.post(url, json={
    'query': q,
    'variables': {'projectId': PROJECT_ID, 'environmentId': ENV_ID, 'serviceId': SVC_ID}
}, headers=headers)

d = r.json()['data']['variables']
for k in [
    'BOT_AD_ENABLED', 'DISABLE_LISANSARENA_AD', 'DISABLE_FROXY_AD', 'DISABLED_AD_ACCOUNTS',
    'TELEGRAM_ADMIN_ID', 'GROUP_DELAY_MIN_SECONDS', 'GROUP_DELAY_MAX_SECONDS',
    'TELEGRAM_API_ID', 'TELEGRAM_API_HASH',
    'LISANSARENA_BOT_TOKEN', 'LISANSARENA_SUPPORT_BOT_TOKEN',
    'BOT_TOKEN', 'KEYVADI_SUPPORT_BOT_TOKEN', 'JARVIS_BOT_TOKEN', 'FROXY_BOT_TOKEN'
]:
    print(f"{k} = {d.get(k)}")
