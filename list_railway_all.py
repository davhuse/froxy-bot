import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = '''
query {
  projects {
    edges {
      node {
        id
        name
        services {
          edges {
            node {
              id
              name
              deployments(first: 1) {
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
  }
}
'''

r = requests.post(url, json={'query': q}, headers=headers)
data = r.json()
for p in data.get('data', {}).get('projects', {}).get('edges', []):
    node = p['node']
    print(f"Project: {node['name']} [{node['id']}]")
    for s in node.get('services', {}).get('edges', []):
        snode = s['node']
        dep = snode.get('deployments', {}).get('edges', [])
        dep_status = dep[0]['node']['status'] if dep else 'NO_DEPLOY'
        print(f"  Service: {snode['name']} [{snode['id']}] -> Status: {dep_status}")
