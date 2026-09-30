# -*- coding: utf-8 -*-
import requests
import json

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

q = """
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
    }
  }
}
"""

r = requests.post('https://backboard.railway.app/graphql/v2', json={'query': q, 'variables': {
    'id': '1dac2884-b5b3-47a2-9160-c42406e88eb7'
}}, headers=headers)
print(json.dumps(r.json(), indent=2))
