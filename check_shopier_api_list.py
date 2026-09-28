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

res = requests.get('https://api.shopier.com/v1/products?limit=20', headers=shopier_headers)
print('GET /products status:', res.status_code)
if res.status_code == 200:
    items = res.json()
    print(f'Total products returned: {len(items)}')
    for item in items:
        pid = item.get('id')
        title = item.get('title')
        stock = item.get('stockQuantity')
        status = item.get('status')
        custom = item.get('customListing')
        media = item.get('media')
        price = item.get('priceData')
        print(f"ID: {pid} | Title: {title} | Stock: {stock} | Status: {status} | Custom: {custom}")
else:
    print(res.text)
