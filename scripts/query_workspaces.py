# -*- coding: utf-8 -*-
import requests
import json

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

q = """
query {
  me {
    id
    email
    workspaces {
      id
      name
    }
  }
}
"""

r = requests.post('https://backboard.railway.app/graphql/v2', json={'query': q}, headers=headers)
print(json.dumps(r.json(), indent=2))
