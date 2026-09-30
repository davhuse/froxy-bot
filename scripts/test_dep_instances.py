# -*- coding: utf-8 -*-
import requests
import json

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

q = """
query GetDeploy($id: String!) {
  deployment(id: $id) {
    id
    status
    canRedeploy
    instances {
      id
      status
    }
  }
}
"""

r = requests.post('https://backboard.railway.app/graphql/v2', json={'query': q, 'variables': {
    'id': '5d3f5d2c-4166-4a99-afc5-3fa13ed6fffd'
}}, headers=headers)
print(json.dumps(r.json(), indent=2))
