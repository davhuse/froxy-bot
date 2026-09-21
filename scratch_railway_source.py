import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = '''
query {
  sourceInput: __type(name: "ServiceSourceInput") {
    inputFields { name type { name kind } }
  }
  projectRepo: __type(name: "ProjectCreateRepo") {
    inputFields { name type { name kind } }
  }
}
'''
r = requests.post(url, json={'query': q}, headers=headers)
print(json.dumps(r.json(), indent=2))
