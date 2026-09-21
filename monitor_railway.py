import requests
import json
import time
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
SVC_ID = '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = '''
query GetDeploys($id: String!) {
  service(id: $id) {
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

for attempt in range(20):
    r = requests.post(url, json={'query': q, 'variables': {'id': SVC_ID}}, headers=headers)
    edges = r.json().get('data', {}).get('service', {}).get('deployments', {}).get('edges', [])
    if edges:
        d = edges[0]['node']
        print(f"[{attempt * 10}s] Deploy {d['id'][:8]} Status: {d['status']}", flush=True)
        if d['status'] == 'SUCCESS':
            print("🎉 RAILWAY DEPLOYMENT IS LIVE & RUNNING!", flush=True)
            break
        elif d['status'] in ('FAILED', 'CRASHED'):
            print(f"❌ Deploy ended with: {d['status']}", flush=True)
            break
    time.sleep(10)
