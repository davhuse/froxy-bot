import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = '''
query GetProj($id: String!) {
  project(id: $id) {
    name
    services {
      edges {
        node {
          id
          name
          deployments(first: 2) {
            edges {
              node {
                id
                status
                createdAt
              }
            }
          }
        }
      }
    }
  }
}
'''

proj_ids = [
  '5fa77867-f818-4da3-b9d9-702529879e6f', # froxy-jarvis-ecosystem
  '63641ae1-05e3-4976-a9bc-d25983d469d8', # lisansarena
  'a3c529c7-dca4-4478-ba78-f36e0777ecd1', # froxy-tg-bot
  '709a7130-b72b-4aaf-9ebb-757011b1e013', # hopeful-luck / froxy-web
  'b6d99f34-7f55-45cc-9565-a3ddd59f61be', # airy-art / froxyai
  'e3c05cfe-d4a6-4066-a9ed-64489341893f', # veridia-studio
  '3417f56d-31a6-4abd-983f-764c2d09c6a4', # nexus-ai-studio-test
  'd589f23e-687d-49c9-aa82-760a491753ce', # aetheria-ai
]

for pid in proj_ids:
    r = requests.post(url, json={'query': q, 'variables': {'id': pid}}, headers=headers)
    pdata = r.json().get('data', {}).get('project')
    if pdata:
        pname = pdata.get('name')
        print(f"Project: {pname} ({pid})")
        for s in pdata.get('services', {}).get('edges', []):
            snode = s['node']
            sname = snode['name']
            sid = snode['id']
            deps = snode.get('deployments', {}).get('edges', [])
            if deps:
                for d in deps:
                    dnode = d['node']
                    print(f"  Service: {sname} ({sid}) -> Deploy: {dnode['id'][:8]} | Status: {dnode['status']} | Created: {dnode['createdAt']}")
            else:
                print(f"  Service: {sname} ({sid}) -> NO DEPLOYMENTS")
