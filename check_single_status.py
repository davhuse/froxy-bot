import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
SERVICE_ID = '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'

q = '''
query GetDeploys($serviceId: String!) {
  service(id: $serviceId) {
    deployments(first: 2) {
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

try:
    r = requests.post(url, json={'query': q, 'variables': {'serviceId': SERVICE_ID}}, headers=headers, timeout=10)
    edges = r.json().get('data', {}).get('service', {}).get('deployments', {}).get('edges', [])
    for e in edges:
        n = e['node']
        print(f"Deployment: {n['id']} | Status: {n['status']} | Created: {n['createdAt']}")
except Exception as exc:
    print(f"Error: {exc}")
