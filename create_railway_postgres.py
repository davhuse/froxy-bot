import requests
import json
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
PROJECT_ID = '5fa77867-f818-4da3-b9d9-702529879e6f'
ENV_ID = '6ea40a3d-d7cc-4675-a593-29f6db038de1'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

# Check mutations on Railway
q_schema = '''
query {
  __type(name: "Mutation") {
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
'''
r = requests.post(url, json={'query': q_schema}, headers=headers)
fields = r.json().get('data', {}).get('__type', {}).get('fields', [])
for f in fields:
    if any(k in f['name'].lower() for k in ['database', 'plugin', 'template', 'postgres']):
        print("Found mutation:", f['name'])
