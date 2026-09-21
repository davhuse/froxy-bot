import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
ENV_ID = '6ea40a3d-d7cc-4675-a593-29f6db038de1'
SVC_ID = '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'

url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = '''
mutation CreateDomain($envId: String!, $svcId: String!) {
  serviceDomainCreate(input: {
    environmentId: $envId,
    serviceId: $svcId
  }) {
    id
    domain
  }
}
'''

variables = {
    'envId': ENV_ID,
    'svcId': SVC_ID
}

r = requests.post(url, json={'query': q, 'variables': variables}, headers=headers)
print("Domain Create Result:", json.dumps(r.json(), indent=2))
