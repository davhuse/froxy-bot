# -*- coding: utf-8 -*-
import requests
import json
import sys

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

def graphql(query, variables=None):
    r = requests.post('https://backboard.railway.app/graphql/v2', json={'query': query, 'variables': variables or {}}, headers=headers, timeout=15)
    return r.json()

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

q_proj = """
query GetProj($id: String!) {
  project(id: $id) {
    name
    environments {
      edges {
        node {
          id
          name
        }
      }
    }
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
"""

q_vars = """
query GetVars($projId: String!, $envId: String!, $svcId: String!) {
  variables(projectId: $projId, environmentId: $envId, serviceId: $svcId)
}
"""

target_token = "8753762842"

for pid in proj_ids:
    res = graphql(q_proj, {'id': pid})
    pdata = res.get('data', {}).get('project')
    if not pdata:
        continue
    pname = pdata.get('name')
    print(f"\n==========================================")
    print(f"Project: {pname} ({pid})")
    envs = [e['node'] for e in pdata.get('environments', {}).get('edges', [])]
    services = [s['node'] for s in pdata.get('services', {}).get('edges', [])]
    
    for s in services:
        sid = s['id']
        sname = s['name']
        for env in envs:
            eid = env['id']
            ename = env['name']
            vres = graphql(q_vars, {'projId': pid, 'envId': eid, 'svcId': sid})
            vdata = vres.get('data', {}).get('variables', {})
            has_match = False
            for k, val in vdata.items():
                if target_token in str(val) or target_token in str(k) or "DIJITAL" in str(k):
                    print(f"  FOUND MATCH in {sname} ({sid}) [Env: {ename}]: {k} = {val[:15]}...")
                    has_match = True
            if not has_match:
                pass
                # print(f"  Checked {sname} ({sid}) [Env: {ename}] - No match")

print("\nDone searching Railway projects.")
