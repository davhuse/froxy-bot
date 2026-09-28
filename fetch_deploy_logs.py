import requests
import json
import sys

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
sys.stdout.reconfigure(encoding='utf-8')

DEP_ID = 'e5c9be18-b220-410a-9dbe-ce90787e91d5'
# First get exact full ID if needed or search deployment
q = '''
query GetDepLogs($deploymentId: String!) {
  deploymentLogs(deploymentId: $deploymentId, limit: 100) {
    message
    timestamp
  }
}
'''
# Let's get service latest deployment ID first
q_dep = '''
query GetLatestDep {
  service(id: "2cc6c23b-25e3-4d37-9cf0-8db3575eca1f") {
    deployments(first: 1) {
      edges {
        node {
          id
          status
        }
      }
    }
  }
}
'''
r_dep = requests.post(url, json={'query': q_dep}, headers=headers)
full_dep_id = r_dep.json()['data']['service']['deployments']['edges'][0]['node']['id']
status = r_dep.json()['data']['service']['deployments']['edges'][0]['node']['status']
print(f"Latest deploy: {full_dep_id} ({status})")

r_logs = requests.post(url, json={'query': q, 'variables': {'deploymentId': full_dep_id}}, headers=headers)
dlogs = r_logs.json().get('data', {}).get('deploymentLogs', [])
print(f"Retrieved {len(dlogs)} logs:")
for l in dlogs[-30:]:
    print(f"[{l.get('timestamp')}] {l.get('message').strip()}")
