# -*- coding: utf-8 -*-
import time
import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

cfg = json.load(open('dijitalpazarim_railway_config.json'))
svc_id = cfg['service_id']

q_list = """
query GetDeployments($svcId: String!) {
  deployments(first: 1, input: { serviceId: $svcId }) {
    edges {
      node {
        id
        status
        createdAt
      }
    }
  }
}
"""

r = requests.post(
    'https://backboard.railway.app/graphql/v2',
    json={'query': q_list, 'variables': {'svcId': svc_id}},
    headers=headers,
    timeout=10
)
edges = r.json().get('data', {}).get('deployments', {}).get('edges', [])
if not edges:
    print("No deployments found for service!")
    sys.exit(1)

latest_dep = edges[0]['node']
dep_id = latest_dep['id']
print(f"Tracking latest Dijital Pazarım Deployment: {dep_id} (Initial status: {latest_dep['status']})")

q_status = """
query GetDeploy($id: String!) {
  deployment(id: $id) {
    id
    status
  }
}
"""

for i in range(25): # up to ~4 minutes
    time.sleep(10)
    res = requests.post(
        'https://backboard.railway.app/graphql/v2',
        json={'query': q_status, 'variables': {'id': dep_id}},
        headers=headers,
        timeout=10
    ).json()
    st = res.get('data', {}).get('deployment', {}).get('status')
    print(f"Poll {i+1} ({(i+1)*10}s): Status = {st}")
    if st == 'SUCCESS':
        print("Dijital Pazarım deployment reached SUCCESS!")
        break
    if st in ['FAILED', 'CRASHED']:
        print(f"Deployment failed with status: {st}")
        break
