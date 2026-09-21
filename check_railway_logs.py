import requests
import json
import sys

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
DEPLOY_ID = 'f37ed5c9-f5e9-40a7-b3dc-b5642fe6c1db'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

sys.stdout.reconfigure(encoding='utf-8')

q_latest = '''
query GetLatestDeploy($serviceId: String!) {
  service(id: $serviceId) {
    deployments(first: 1) {
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
'''
SERVICE_ID = '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'
r_dep = requests.post(url, json={'query': q_latest, 'variables': {'serviceId': SERVICE_ID}}, headers=headers)
edges = r_dep.json().get('data', {}).get('service', {}).get('deployments', {}).get('edges', [])
if edges:
    DEPLOY_ID = edges[0]['node']['id']
    status = edges[0]['node']['status']
    print(f"Latest deploy: {DEPLOY_ID} status: {status}")

if status == 'BUILDING':
    q_b = '''
    query GetBuildLogs($id: String!) {
      buildLogs(deploymentId: $id, limit: 30) {
        message
      }
    }
    '''
    r_b = requests.post(url, json={'query': q_b, 'variables': {'id': DEPLOY_ID}}, headers=headers)
    for l in r_b.json().get('data', {}).get('buildLogs', [])[-10:]:
        print(l.get('message', '').strip())
else:
    q = '''
    query GetLogs($id: String!) {
      deploymentLogs(deploymentId: $id, limit: 50) {
        message
        severity
        timestamp
      }
    }
    '''
    r = requests.post(url, json={'query': q, 'variables': {'id': DEPLOY_ID}}, headers=headers)
    logs = r.json().get('data', {}).get('deploymentLogs', [])
    if logs:
        for line in logs[-20:]:
            print(line.get('message', '').strip())
    else:
        print('No logs or response:', r.json())
