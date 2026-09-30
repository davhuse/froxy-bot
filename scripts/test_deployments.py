# -*- coding: utf-8 -*-
import requests
import json

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
q = """
query GetDeployments($svcId: String!) {
  deployments(input: { serviceId: $svcId }, first: 10) {
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
"""
r = requests.post('https://backboard.railway.app/graphql/v2', json={'query': q, 'variables': {
    'svcId': '7b5b4cf2-470f-497d-9c27-b4a8a021635d'
}}, headers=headers)
print(json.dumps(r.json(), indent=2))
