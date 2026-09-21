import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = '''
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
'''
r = requests.post(url, json={'query': q}, headers=headers)
print("Workspaces Result:", json.dumps(r.json(), indent=2))
