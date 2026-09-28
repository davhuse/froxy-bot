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
for k, v in r.json().get('data', {}).get('variables', {}).items():
    os.environ[k] = v

from lisansarena_store import get_store
store = get_store(force_retry=True)

# Create or get a test user
user_id = store.get_or_create_user({'id': 123456789, 'username': 'testuser', 'first_name': 'Test', 'last_name': 'User'})
print('User ID:', user_id)

print('\n--- 1. Testing package topup (100 TL) ---')
try:
    res = store.create_topup(user_id, 10000, mode='package')
    print('Package topup SUCCESS:', res)
except Exception as e:
    import traceback
    traceback.print_exc()

print('\n--- 2. Testing custom topup (50 TL) ---')
try:
    res = store.create_topup(user_id, 5000, mode='custom')
    print('Custom topup SUCCESS:', res)
except Exception as e:
    import traceback
    traceback.print_exc()

print('\n--- 3. Testing purchase with zero balance ---')
products = store.storefront_catalog()
first_avail = next((p for p in products if p['available']), None)
if first_avail:
    print('Trying to purchase product:', first_avail['id'], first_avail['name'])
    try:
        store.purchase(user_id, first_avail['id'], 1)
    except Exception as e:
        print('Purchase with 0 balance:', type(e), e)
