import requests
import json

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
print('AD_STRING_SESSION_JARVIS:', bool(vars.get('AD_STRING_SESSION_JARVIS')), len(vars.get('AD_STRING_SESSION_JARVIS', '')))
print('AD_STRING_SESSION_LISANSARENA:', bool(vars.get('AD_STRING_SESSION_LISANSARENA')), len(vars.get('AD_STRING_SESSION_LISANSARENA', '')))
print('AD_STRING_SESSION_KEYVADI:', bool(vars.get('AD_STRING_SESSION_KEYVADI')), len(vars.get('AD_STRING_SESSION_KEYVADI', '')))
print('AD_STRING_SESSION_FROXY:', bool(vars.get('AD_STRING_SESSION_FROXY')), len(vars.get('AD_STRING_SESSION_FROXY', '')))
