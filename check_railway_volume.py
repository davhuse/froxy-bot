import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = """
query {
  __type(name: "Mutation") {
    fields {
      name
    }
  }
}
"""
r = requests.post(url, json={'query': q}, headers=headers)
fields = [f['name'] for f in r.json().get('data', {}).get('__type', {}).get('fields', [])]
print("Volume mutations:", [f for f in fields if 'volume' in f.lower()])
