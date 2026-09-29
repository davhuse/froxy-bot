# -*- coding: utf-8 -*-
import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
query = """
query {
  me {
    id
    name
    email
    projects {
      edges {
        node {
          id
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
              }
            }
          }
        }
      }
    }
  }
}
"""

r = requests.post(
    'https://backboard.railway.app/graphql/v2',
    json={'query': query},
    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
)

if r.status_code != 200:
    print(f"Error {r.status_code}: {r.text}")
    sys.exit(1)

data = r.json()
projects = data.get('data', {}).get('me', {}).get('projects', {}).get('edges', [])
print(f"Total projects found: {len(projects)}")
for p in projects:
    node = p['node']
    print(f"\nProject: {node['name']} (ID: {node['id']})")
    envs = [e['node']['name'] for e in node.get('environments', {}).get('edges', [])]
    print(f"  Environments: {', '.join(envs)}")
    for s in node.get('services', {}).get('edges', []):
        print(f"  Service: {s['node']['name']} (ID: {s['node']['id']})")
