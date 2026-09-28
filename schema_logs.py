import requests
import json
import sys

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
sys.stdout.reconfigure(encoding='utf-8')

q = '''
query SchemaLogs {
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
'''
r = requests.post(url, json={'query': q}, headers=headers)
fields = r.json().get('data', {}).get('__type', {}).get('fields', [])
for f in fields:
    if f['name'] in ['deploymentLogs', 'environmentLogs', 'httpLogs']:
        print(f['name'], json.dumps(f['args'], indent=2))
