import requests, json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
q = """
query GetVars($projId: String!, $envId: String!, $svcId: String!) {
  variables(projectId: $projId, environmentId: $envId, serviceId: $svcId)
}
"""
r = requests.post(url, json={'query': q, 'variables': {
    'projId': '5fa77867-f818-4da3-b9d9-702529879e6f',
    'envId': '6ea40a3d-d7cc-4675-a593-29f6db038de1',
    'svcId': '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'
}}, headers=headers)
vars = r.json().get('data', {}).get('variables', {})
for k in sorted(vars.keys()):
    if any(x in k.lower() for x in ['lisans', 'shopier', 'database', 'postgres']):
        val = vars[k]
        if 'token' in k.lower() or 'key' in k.lower() or 'secret' in k.lower() or 'password' in k.lower():
            val = val[:8] + '...' if val else 'EMPTY'
        print(f'{k} = {val}')
