import requests
import json
import sys

if sys.platform.startswith('win'):
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
        }
      }
    }
  }
}
'''

proj_ids = [
  'e3c05cfe-d4a6-4066-a9ed-64489341893f',
  'a3c529c7-dca4-4478-ba78-f36e0777ecd1',
  '709a7130-b72b-4aaf-9ebb-757011b1e013',
  '1dac2884-b5b3-47a2-9160-c42406e88eb7',
  '3417f56d-31a6-4abd-983f-764c2d09c6a4',
  'd589f23e-687d-49c9-aa82-760a491753ce',
  '63641ae1-05e3-4976-a9bc-d25983d469d8',
  'b6d99f34-7f55-45cc-9565-a3ddd59f61be'
]

for pid in proj_ids:
    r = requests.post(url, json={'query': q, 'variables': {'id': pid}}, headers=headers)
    pdata = r.json().get('data', {}).get('project')
    if pdata:
        svcs = [s['node']['name'] + ' (' + s['node']['id'] + ')' for s in pdata.get('services', {}).get('edges', [])]
        print(f"{pdata.get('name')} [{pid}]: {svcs}")
