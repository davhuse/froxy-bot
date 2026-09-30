# -*- coding: utf-8 -*-
import requests
import json

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

def graphql(query, variables=None):
    r = requests.post('https://backboard.railway.app/graphql/v2', json={'query': query, 'variables': variables or {}}, headers=headers, timeout=15)
    return r.json()

q_all = """
query {
  me {
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
                deployments(first: 5) {
                  edges {
                    node {
                      id
                      status
                      createdAt
                      environmentId
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
}
"""

res = graphql(q_all)
projects = res.get('data', {}).get('me', {}).get('projects', {}).get('edges', [])
for p in projects:
    pnode = p['node']
    pname = pnode['name']
    pid = pnode['id']
    for s in pnode.get('services', {}).get('edges', []):
        snode = s['node']
        sname = snode['name']
        sid = snode['id']
        for d in snode.get('deployments', {}).get('edges', []):
            dnode = d['node']
            if dnode['status'] == 'SUCCESS':
                print(f"ACTIVE: Project '{pname}' ({pid}) -> Svc '{sname}' ({sid}) -> Deploy {dnode['id']} (Env: {dnode['environmentId']})")

