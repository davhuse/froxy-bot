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
          ofType {
            name
            kind
          }
        }
      }
    }
  }
}
"""

r = requests.post('https://backboard.railway.app/graphql/v2', json={'query': q}, headers=headers)
fields = r.json().get('data', {}).get('__type', {}).get('fields', [])
for f in fields:
    if f['name'] in ['projects', 'workspace', 'me', 'userProfile']:
        print(f"Field: {f['name']}")
        for a in f['args']:
            print(f"  Arg: {a['name']}")
