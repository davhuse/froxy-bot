import requests
import json
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
SERVICE_ID = '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'
GRAPHQL_URL = 'https://backboard.railway.app/graphql/v2'
HEADERS = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q_latest = '''
query GetLatestDeploy($serviceId: String!) {
  service(id: $serviceId) {
    deployments(first: 3) {
      edges {
        node {
          id
          status
          createdAt
          meta
        }
      }
    }
  }
}
'''

print("Waiting for Railway deployment for commit 7f9e1f9...")

for attempt in range(30):
    time.sleep(8)
    try:
        r = requests.post(GRAPHQL_URL, json={'query': q_latest, 'variables': {'serviceId': SERVICE_ID}}, headers=HEADERS)
        edges = r.json().get('data', {}).get('service', {}).get('deployments', {}).get('edges', [])
        if not edges:
            print(f"[{attempt+1}] No deployments found yet...")
            continue
        dep = edges[0]['node']
        dep_id = dep['id']
        status = dep['status']
        created = dep['createdAt']
        meta = dep.get('meta') or {}
        commit = meta.get('commitHash', '')[:7] if isinstance(meta, dict) else ''
        print(f"[{attempt+1}] Latest deploy: {dep_id} status: {status} commit: {commit} created: {created}")
        
        if status == 'SUCCESS':
            print(f"\n[OK] Deployment {dep_id} succeeded!")
            break
        elif status in ('FAILED', 'CRASHED'):
            print(f"\n[FAIL] Deployment {dep_id} failed with status {status}!")
            break
    except Exception as e:
        print(f"Error checking deployment: {e}")
