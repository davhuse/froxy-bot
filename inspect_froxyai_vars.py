import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q_vars = '''
query GetVars($projectId: String!, $environmentId: String!, $serviceId: String!) {
  variables(projectId: $projectId, environmentId: $environmentId, serviceId: $serviceId)
}
'''

r = requests.post(url, json={
    'query': q_vars,
    'variables': {
        'projectId': 'b6d99f34-7f55-45cc-9565-a3ddd59f61be',
        'environmentId': 'c76e568d-5ccd-4cc8-91c5-627080b43314',
        'serviceId': 'e3e77cac-a6f6-48cc-9641-32b7075261a8'
    }
}, headers=headers)
print("=== AIRY-ART FROXYAI VARS ===")
print(json.dumps(r.json(), indent=2))
