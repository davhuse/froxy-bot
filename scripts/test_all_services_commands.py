# -*- coding: utf-8 -*-
import requests
import json

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

q = """
query GetProj($id: String!) {
  project(id: $id) {
    name
    services {
      edges {
        node {
          id
          name
          serviceInstances {
            edges {
              node {
                startCommand
                buildCommand
              }
            }
          }
        }
      }
    }
  }
}
"""

proj_ids = [
    '6514ed43-720f-4e66-8ad3-590c1e445bb2', # dijital pazarim
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
    r = requests.post('https://backboard.railway.app/graphql/v2', json={'query': q, 'variables': {'id': pid}}, headers=headers)
    pdata = r.json().get('data', {}).get('project')
    if not pdata:
        continue
    pname = pdata.get('name')
    for s in pdata.get('services', {}).get('edges', []):
        sn = s['node']
        sname = sn['name']
        sid = sn['id']
        instances = sn.get('serviceInstances', {}).get('edges', [])
        cmds = []
        for inst in instances:
            inode = inst['node']
            cmds.append(f"start: {inode.get('startCommand')}, build: {inode.get('buildCommand')}")
        print(f"Project '{pname}' -> Service '{sname}' ({sid}): {cmds}")
