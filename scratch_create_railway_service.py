import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
PROJECT_ID = '5fa77867-f818-4da3-b9d9-702529879e6f'
ENV_ID = '6ea40a3d-d7cc-4675-a593-29f6db038de1'

url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = '''
mutation CreateSvc($projId: String!, $source: ServiceSourceInput, $branch: String) {
  serviceCreate(input: {
    projectId: $projId,
    name: "bot-service",
    source: $source,
    branch: $branch
  }) {
    id
    name
  }
}
'''

variables = {
    'projId': PROJECT_ID,
    'source': {'repo': 'davhuse/froxy-bot'},
    'branch': 'main'
}

r = requests.post(url, json={'query': q, 'variables': variables}, headers=headers)
print("Service Create Result:", json.dumps(r.json(), indent=2))
