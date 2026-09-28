import requests
import sys

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
sys.stdout.reconfigure(encoding='utf-8')
SERVICE_ID = '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'

q = """
query GetDeploys($serviceId: String!) {
  service(id: $serviceId) {
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
"""
r = requests.post(url, json={'query': q, 'variables': {'serviceId': SERVICE_ID}}, headers=headers, timeout=10)
dep = r.json().get('data', {}).get('service', {}).get('deployments', {}).get('edges', [])[0]['node']
print(f"Deployment: {dep['id'][:8]} -> {dep['status']}")

q_logs = """
query GetBuildLogs($id: String!) {
  buildLogs(deploymentId: $id, limit: 15) {
    message
  }
}
"""
r2 = requests.post(url, json={'query': q_logs, 'variables': {'id': dep['id']}}, headers=headers, timeout=10)
logs = r2.json().get('data', {}).get('buildLogs', []) or []
for l in logs[-10:]:
    print(l.get('message', '').strip())
