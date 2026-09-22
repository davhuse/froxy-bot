import requests
import json
import sys

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
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
    dep = edges[0]['node']
    dep_id = dep['id']
    status = dep['status']
    print(f"Latest deploy: {dep_id} status: {status}")
    
    q_logs = '''
    query GetLogs($deploymentId: String!) {
      deploymentLogs(deploymentId: $deploymentId, limit: 100) {
        message
        timestamp
      }
    }
    '''
    r_logs = requests.post(url, json={'query': q_logs, 'variables': {'deploymentId': dep_id}}, headers=headers)
    logs = r_logs.json().get('data', {}).get('deploymentLogs', [])
    for l in logs:
        print(f"[{l.get('timestamp')}] {l.get('message')}")
