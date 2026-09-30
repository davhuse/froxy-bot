# -*- coding: utf-8 -*-
import requests
import json

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
q = """
query GetLogs($depId: String!) {
  deploymentLogs(deploymentId: $depId, limit: 100) {
    message
    timestamp
  }
}
"""
r = requests.post('https://backboard.railway.app/graphql/v2', json={'query': q, 'variables': {
    'depId': '5d3f5d2c-4166-4a99-afc5-3fa13ed6fffd'
}}, headers=headers)
logs = r.json().get('data', {}).get('deploymentLogs', [])
for l in logs[-30:]:
    print(f"[{l.get('timestamp')}] {l.get('message')}")
