import os, requests, json

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
shopier_token = vars.get('SHOPIER_LISANSARENA_ACCESS_TOKEN')

shopier_headers = {
    'Authorization': f'Bearer {shopier_token}',
    'Content-Type': 'application/json'
}

# Fetch details of product 49847044 (100 TL) and 51063055 (new custom)
for pid in ['49847044', '51063055']:
    res = requests.get(f'https://api.shopier.com/v1/products/{pid}', headers=shopier_headers)
    print(f"Product {pid} status: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(res.text)
