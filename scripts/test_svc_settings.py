# -*- coding: utf-8 -*-
import requests
import json

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

q = """
query GetSvc($id: String!) {
  service(id: $id) {
    id
    name
    serviceInstances {
      edges {
        node {
          id
          environmentId
          startCommand
          buildCommand
          rootDirectory
          healthcheckPath
        }
      }
    }
  }
}
"""
r = requests.post('https://backboard.railway.app/graphql/v2', json={'query': q, 'variables': {
    'id': '7b5b4cf2-470f-497d-9c27-b4a8a021635d'
}}, headers=headers)
print(json.dumps(r.json(), indent=2))
