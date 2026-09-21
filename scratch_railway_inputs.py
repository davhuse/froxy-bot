import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = '''
query {
  projectCreate: __type(name: "ProjectCreateInput") {
    inputFields { name type { name kind ofType { name } } }
  }
  serviceCreate: __type(name: "ServiceCreateInput") {
    inputFields { name type { name kind ofType { name } } }
  }
  variableCollectionUpsert: __type(name: "VariableCollectionUpsertInput") {
    inputFields { name type { name kind ofType { name } } }
  }
  serviceDomainCreate: __type(name: "ServiceDomainCreateInput") {
    inputFields { name type { name kind ofType { name } } }
  }
}
'''
r = requests.post(url, json={'query': q}, headers=headers)
print(json.dumps(r.json(), indent=2))
