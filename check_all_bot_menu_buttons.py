import os
import json
import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
q = '''
query GetVars($projId: String!, $envId: String!, $svcId: String!) {
  variables(projectId: $projId, environmentId: $envId, serviceId: $svcId)
}
'''
r = requests.post(url, json={'query': q, 'variables': {
    'projId': '5fa77867-f818-4da3-b9d9-702529879e6f',
    'envId': '6ea40a3d-d7cc-4675-a593-29f6db038de1',
    'svcId': '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'
}}, headers=headers)
vars = r.json().get('data', {}).get('variables', {})

bot_tokens = {
    'keyvadi': vars.get('KEYVADI_SUPPORT_BOT_TOKEN'),
    'lisansarena': vars.get('LISANSARENA_BOT_TOKEN') or vars.get('LISANSARENA_SUPPORT_BOT_TOKEN'),
    'froxy': vars.get('FROXY_SUPPORT_BOT_TOKEN') or vars.get('FROXY_BOT_TOKEN'),
    'jarvis': vars.get('JARVIS_BOT_TOKEN') or vars.get('BOT_TOKEN')
}

for name, tok in bot_tokens.items():
    if tok:
        resp = requests.get(f'https://api.telegram.org/bot{tok}/getChatMenuButton').json()
        me = requests.get(f'https://api.telegram.org/bot{tok}/getMe').json()
        print(f"{name} (@{me.get('result', {}).get('username')}):")
        print(f"   MenuButton: {resp.get('result')}")
    else:
        print(f"{name}: NO TOKEN FOUND")
