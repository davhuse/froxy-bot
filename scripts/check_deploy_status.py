# -*- coding: utf-8 -*-
import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

query = """
query GetDeployments($svcId: String!) {
  deployments(input: { serviceId: $svcId }, first: 3) {
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
"""

def check_service(name, svc_id):
    print(f"\n=== {name} ({svc_id}) ===")
    r = requests.post(
        'https://backboard.railway.app/graphql/v2',
        json={'query': query, 'variables': {'svcId': svc_id}},
        headers=headers,
        timeout=10
    )
    data = r.json()
    edges = data.get('data', {}).get('deployments', {}).get('edges', [])
    for edge in edges:
        node = edge['node']
        meta = node.get('meta') or {}
        commit = meta.get('commitMessage') or meta.get('commitAuthor') or ''
        print(f"ID: {node['id']} | Status: {node['status']} | Created: {node['createdAt']} | Commit: {commit}")

main_svc_id = "2cc6c23b-25e3-4d37-9cf0-8db3575eca1f"
dp_svc_id = "7b5b4cf2-470f-497d-9c27-b4a8a021635d"

check_service("Main Bot Service (KeyVadi/LA/Froxy)", main_svc_id)
check_service("Dijital Pazarim Service", dp_svc_id)
