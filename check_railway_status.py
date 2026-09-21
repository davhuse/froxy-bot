import requests
import json
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
SVC_ID = '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = '''
query GetDeploys($id: String!) {
  service(id: $id) {
    id
    name
    deployments {
      edges {
        node {
          id
          status
          createdAt
        }
      }
    }
  }
}
'''
r = requests.post(url, json={'query': q, 'variables': {'id': SVC_ID}}, headers=headers)
print(json.dumps(r.json(), indent=2))
