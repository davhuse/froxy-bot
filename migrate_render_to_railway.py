import requests
import json
import time
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

# ─── 1. Credentials & IDs ───
RENDER_KEY = 'rnd_4c83vU85zEZ7KOjaS5crYqM4x55G'
RENDER_SERVICE_ID = 'srv-danfkkek1f9s738iq5rg'

RAILWAY_TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
RAILWAY_PROJECT_ID = '5fa77867-f818-4da3-b9d9-702529879e6f'
RAILWAY_ENV_ID = '6ea40a3d-d7cc-4675-a593-29f6db038de1'
RAILWAY_SERVICE_ID = '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'
RAILWAY_GRAPHQL = 'https://backboard.railway.app/graphql/v2'

railway_headers = {
    'Authorization': f'Bearer {RAILWAY_TOKEN}',
    'Content-Type': 'application/json'
}

print("==================================================")
print("🚀 MIGRATION: RENDER -> RAILWAY (ZERO DOWNTIME/CONFLICT)")
print("==================================================")

# Step 1: Suspend Render to release MTProto session locks
print("\n[1/3] Suspending Render service to release Telegram sessions...")
render_headers = {
    'Authorization': f'Bearer {RENDER_KEY}',
    'Accept': 'application/json'
}
try:
    r_suspend = requests.post(f'https://api.render.com/v1/services/{RENDER_SERVICE_ID}/suspend', headers=render_headers, timeout=10)
    print(f"Render suspend status: {r_suspend.status_code}")
except Exception as e:
    print(f"Render suspend warning: {e}")

time.sleep(3)

# Step 2: Trigger Deploy on Railway
print("\n[2/3] Triggering deploy on Railway with latest GitHub commit...")
deploy_mutation = '''
mutation DeploySvc($svcId: String!, $envId: String!) {
  serviceInstanceDeploy(
    serviceId: $svcId,
    environmentId: $envId,
    latestCommit: true
  )
}
'''
r_deploy = requests.post(
    RAILWAY_GRAPHQL,
    json={
        'query': deploy_mutation,
        'variables': {
            'svcId': RAILWAY_SERVICE_ID,
            'envId': RAILWAY_ENV_ID
        }
    },
    headers=railway_headers,
    timeout=15
)
print("Railway deploy response:", r_deploy.json())

# Step 3: Poll Railway Deployment Status
print("\n[3/3] Monitoring Railway deployment...")
poll_query = '''
query GetDeployments($svcId: String!) {
  deployments(input: { serviceId: $svcId }, first: 1) {
    edges {
      node {
        id
        status
        createdAt
        url
      }
    }
  }
}
'''

for i in range(15):
    try:
        r_poll = requests.post(
            RAILWAY_GRAPHQL,
            json={'query': poll_query, 'variables': {'svcId': RAILWAY_SERVICE_ID}},
            headers=railway_headers,
            timeout=10
        )
        edges = r_poll.json().get('data', {}).get('deployments', {}).get('edges', [])
        if edges:
            node = edges[0]['node']
            print(f"[{i*5}s] Deployment ID: {node['id']} | Status: {node['status']}")
            if node['status'] in ('SUCCESS', 'FAILED', 'CRASHED'):
                print(f"Deployment finished with status: {node['status']}")
                break
    except Exception as e:
        print(f"Poll error: {e}")
    time.sleep(5)

print("\n==================================================")
print("✅ Migration triggered successfully!")
print("Public Domain: https://bot-service-production-9d74.up.railway.app")
print("==================================================")
