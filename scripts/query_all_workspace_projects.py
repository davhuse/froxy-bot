# -*- coding: utf-8 -*-
import requests
import json

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

q = """
query {
  projects(workspaceId: "a1d9b117-462a-4a18-9850-cd11379cde08") {
    edges {
      node {
        id
        name
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
"""

r = requests.post('https://backboard.railway.app/graphql/v2', json={'query': q}, headers=headers)
data = r.json()
projects = data.get('data', {}).get('projects', {}).get('edges', [])
print(f"Total projects found: {len(projects)}")
for p in projects:
    node = p['node']
    print(f"\nProject: {node['name']} ({node['id']})")
    for s in node.get('services', {}).get('edges', []):
        sn = s['node']
        print(f"  - Service: {sn['name']} ({sn['id']})")

