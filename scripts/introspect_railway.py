# -*- coding: utf-8 -*-
import requests
import json

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

q = """
query {
  __type(name: "Query") {
    fields {
      name
      args {
        name
        type {
          name
          kind
        }
      }
    }
  }
}
"""

r = requests.post('https://backboard.railway.app/graphql/v2', json={'query': q}, headers=headers)
fields = r.json().get('data', {}).get('__type', {}).get('fields', [])
for f in fields:
    if any(k in f['name'].lower() for k in ['proj', 'user', 'me', 'work', 'team']):
        print(f"Field: {f['name']}")
