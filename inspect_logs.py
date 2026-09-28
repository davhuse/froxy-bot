import requests
import json
import sys
from datetime import datetime, timezone, timedelta

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
sys.stdout.reconfigure(encoding='utf-8')

ENV_ID = '6ea40a3d-d7cc-4675-a593-29f6db038de1'
SERVICE_ID = '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'

print("=== 1. Checking Environment Logs ===")
q_env = '''
query GetEnvLogs($envId: String!, $beforeLimit: Int) {
  environmentLogs(environmentId: $envId, beforeLimit: $beforeLimit) {
    message
    timestamp
    severity
  }
}
'''
r = requests.post(url, json={'query': q_env, 'variables': {'envId': ENV_ID, 'beforeLimit': 500}}, headers=headers)
env_logs = r.json().get('data', {}).get('environmentLogs', [])
print(f"Total environmentLogs: {len(env_logs)}")
if env_logs:
    for l in env_logs[-50:]:
        print(f"[{l.get('timestamp')}] {l.get('message')}")

print("\n=== 2. Checking Deployment Logs with startDate ===")
q_dep = '''
query GetDepLogs($deploymentId: String!, $startDate: String, $limit: Int) {
  deploymentLogs(deploymentId: $deploymentId, startDate: $startDate, limit: $limit) {
    message
    timestamp
    severity
  }
}
'''
# Fetch latest deploy
q_latest = '''
query GetLatestDeploy($serviceId: String!) {
  service(id: $serviceId) {
    deployments(first: 3) {
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
r_dep = requests.post(url, json={'query': q_latest, 'variables': {'serviceId': SERVICE_ID}}, headers=headers)
edges = r_dep.json().get('data', {}).get('service', {}).get('deployments', {}).get('edges', [])
for edge in edges:
    node = edge['node']
    dep_id = node['id']
    st = node['status']
    print(f"\n--- Deployment: {dep_id} ({st}) created {node['createdAt']} ---")
    
    r_l = requests.post(url, json={'query': q_dep, 'variables': {'deploymentId': dep_id, 'limit': 300}}, headers=headers)
    d_logs = r_l.json().get('data', {}).get('deploymentLogs', [])
    print(f"Deployment logs found: {len(d_logs)}")
    for l in d_logs[-50:]:
        print(f"[{l.get('timestamp')}] {l.get('message')}")
