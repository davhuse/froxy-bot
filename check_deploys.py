import requests
import json
import sys

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
q = """
query GetDeploys($serviceId: String!) {
  service(id: $serviceId) {
    deployments(first: 3) {
      edges {
        node {
          id
          status
          createdAt
          meta
        }
      }
    }
  }
}
"""
r = requests.post(url, json={'query': q, 'variables': {'serviceId': '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'}}, headers=headers)
edges = r.json().get('data', {}).get('service', {}).get('deployments', {}).get('edges', [])
for e in edges:
    n = e['node']
    commit = n.get('meta', {}).get('commitHash', '')[:7] if n.get('meta') else ''
    msg = n.get('meta', {}).get('commitMessage', '') if n.get('meta') else ''
    print(f"Deploy {n['id']} | Status: {n['status']} | Created: {n['createdAt']} | Commit: {commit} - {msg}")
