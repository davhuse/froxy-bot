import requests
import json
import sys

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
sys.stdout.reconfigure(encoding='utf-8')

ENV_ID = '6ea40a3d-d7cc-4675-a593-29f6db038de1'

# Query logs without anchorDate, just latest beforeLimit
q = '''
query GetRecentLogs($envId: String!, $beforeLimit: Int) {
  environmentLogs(environmentId: $envId, beforeLimit: $beforeLimit) {
    message
    timestamp
  }
}
'''
r = requests.post(url, json={'query': q, 'variables': {'envId': ENV_ID, 'beforeLimit': 50}}, headers=headers)
logs = r.json().get('data', {}).get('environmentLogs', [])
print(f"Total retrieved: {len(logs)}")
for l in logs[-30:]:
    msg = l.get('message', '').strip()
    ts = l.get('timestamp', '')
    print(f"[{ts}] {msg}")
