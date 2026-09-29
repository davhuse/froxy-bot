# -*- coding: utf-8 -*-
"""Trigger deploy on Railway for Dijital Pazarım and monitor status."""

import requests
import json
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

with open('dijitalpazarim_railway_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

svc_id = cfg['service_id']
env_id = cfg['environment_id']
domain = cfg.get('domain', 'dijital-pazarim-service-production.up.railway.app')

print(f"Triggering deploy for Service {svc_id} in Environment {env_id}...")
mutation_deploy = """
mutation DeploySvc($svcId: String!, $envId: String!) {
  serviceInstanceDeploy(
    serviceId: $svcId,
    environmentId: $envId,
    latestCommit: true
  )
}
"""

r_deploy = requests.post(
    'https://backboard.railway.app/graphql/v2',
    json={'query': mutation_deploy, 'variables': {'svcId': svc_id, 'envId': env_id}},
    headers=headers,
    timeout=15
)
print("Deploy trigger response:", r_deploy.json())

# Monitor deployment
print("\nMonitoring deployment progress...")
query_poll = """
query GetDeployments($svcId: String!) {
  deployments(input: { serviceId: $svcId }, first: 1) {
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

for i in range(24):
    time.sleep(5)
    try:
        r_poll = requests.post(
            'https://backboard.railway.app/graphql/v2',
            json={'query': query_poll, 'variables': {'svcId': svc_id}},
            headers=headers,
            timeout=10
        )
        edges = r_poll.json().get('data', {}).get('deployments', {}).get('edges', [])
        if edges:
            node = edges[0]['node']
            status = node['status']
            print(f"[{(i+1)*5}s] Deployment ID: {node['id']} | Status: {status}")
            if status in ('SUCCESS', 'CRASHED', 'FAILED'):
                print(f"\nFinal Deployment Status: {status}")
                break
    except Exception as e:
        print(f"Polling warning: {e}")

print(f"\nPublic URL: https://{domain}")
print(f"Mini App URL: https://{domain}/dp")
