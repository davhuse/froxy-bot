import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = '''
query {
  __type(name: "Mutation") {
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
'''
r = requests.post(url, json={'query': q}, headers=headers)
fields = {f['name']: f['args'] for f in r.json()['data']['__type']['fields']}
for m in ['projectCreate', 'serviceCreate', 'variableCollectionUpsert', 'serviceDomainCreate', 'githubRepoDeploy']:
    print(m, json.dumps(fields.get(m), indent=2))
