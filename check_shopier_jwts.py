import json, base64

with open('check_la_vars.py') as f:
    pass

import requests
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

for k in ['SHOPIER_LISANSARENA_ACCESS_TOKEN', 'SHOPIER_KEYVADI_ACCESS_TOKEN', 'SHOPIER_FROXY_ACCESS_TOKEN', 'SHOPIER_JARVIS_ACCESS_TOKEN']:
    token = vars.get(k)
    print(f"--- {k} ---")
    if token and '.' in token:
        parts = token.split('.')
        payload_b64 = parts[1]
        payload_b64 += '=' * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()))
        import datetime
        exp = payload.get('exp')
        exp_dt = datetime.datetime.fromtimestamp(exp, tz=datetime.timezone.utc) if exp else 'No exp'
        print(f"Sub: {payload.get('sub')}")
        print(f"Scopes: {payload.get('scopes') or payload.get('scope')}")
        print(f"Expires: {exp_dt}")
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        print(f"Expired: {exp_dt < now if exp else False}")
    else:
        print("Not a JWT or empty:", token[:10] if token else 'None')
