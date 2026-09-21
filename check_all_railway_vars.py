import requests
import json
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = '''
query GetVars($projId: String!, $envId: String!, $svcId: String!) {
  variables(projectId: $projId, environmentId: $envId, serviceId: $svcId)
}
'''

# Get environments for each project
q_proj = '''
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
'''

proj_ids = [
  'e3c05cfe-d4a6-4066-a9ed-64489341893f',
  'a3c529c7-dca4-4478-ba78-f36e0777ecd1',
  '709a7130-b72b-4aaf-9ebb-757011b1e013',
  '3417f56d-31a6-4abd-983f-764c2d09c6a4',
  'd589f23e-687d-49c9-aa82-760a491753ce',
  '63641ae1-05e3-4976-a9bc-d25983d469d8',
  'b6d99f34-7f55-45cc-9565-a3ddd59f61be'
]

for pid in proj_ids:
    r = requests.post(url, json={'query': q_proj, 'variables': {'id': pid}}, headers=headers)
    pdata = r.json().get('data', {}).get('project')
    if not pdata: continue
    envs = pdata.get('environments', {}).get('edges', [])
    svcs = pdata.get('services', {}).get('edges', [])
    if not envs or not svcs: continue
    env_id = envs[0]['node']['id']
    for s in svcs:
        sid = s['node']['id']
        sname = s['node']['name']
        r_vars = requests.post(url, json={'query': q, 'variables': {'projId': pid, 'envId': env_id, 'svcId': sid}}, headers=headers)
        vdata = r_vars.json().get('data', {}).get('variables', {})
        for k, v in vdata.items():
            if '8940174381' in str(v) or 'A_ToolsX' in str(v) or 'jarvis' in k.lower():
                print(f"FOUND MATCH in {pdata['name']} / {sname}: {k} = {v}")
