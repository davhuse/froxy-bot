import requests
import time

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
SERVICE_ID = '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'

q = '''
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
'''

for i in range(12):
    time.sleep(10)
    try:
        r = requests.post(url, json={'query': q, 'variables': {'serviceId': SERVICE_ID}}, headers=headers, timeout=10)
        edges = r.json().get('data', {}).get('service', {}).get('deployments', {}).get('edges', [])
        if edges:
            node = edges[0]['node']
            dep_id = node['id']
            status = node['status']
            print(f"[{i+1}/12] {dep_id[:8]} -> {status}", flush=True)
            if status in ('SUCCESS', 'FAILED', 'CRASHED'):
                break
    except Exception as e:
        print(f"Error: {e}", flush=True)
