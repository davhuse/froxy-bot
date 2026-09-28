import requests
import json
import sys

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = '''
query GetProj($id: String!) {
  project(id: $id) {
    name
    environments {
      edges {
        node {
          id
          name
        }
      }
    }
    services {
      edges {
        node {
          id
          name
          deployments(first: 3) {
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
    }
  }
}
'''

for pid in ['b6d99f34-7f55-45cc-9565-a3ddd59f61be', '709a7130-b72b-4aaf-9ebb-757011b1e013', '5fa77867-f818-4da3-b9d9-702529879e6f']:
    r = requests.post(url, json={'query': q, 'variables': {'id': pid}}, headers=headers)
    print(f"=== PROJECT {pid} ===")
    print(json.dumps(r.json(), indent=2))
