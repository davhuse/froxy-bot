import requests
import json
import sys
from datetime import datetime, timezone

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
sys.stdout.reconfigure(encoding='utf-8')

ENV_ID = '6ea40a3d-d7cc-4675-a593-29f6db038de1'
now_iso = datetime.now(timezone.utc).isoformat()

q = '''
query GetRecentLogs($envId: String!, $anchorDate: String, $beforeLimit: Int) {
  environmentLogs(environmentId: $envId, anchorDate: $anchorDate, beforeLimit: $beforeLimit) {
    message
    timestamp
  }
}
'''
r = requests.post(url, json={'query': q, 'variables': {'envId': ENV_ID, 'anchorDate': now_iso, 'beforeLimit': 80}}, headers=headers)
logs = r.json().get('data', {}).get('environmentLogs', [])
print(f"Total retrieved: {len(logs)}")
for l in logs[-35:]:
    msg = l.get('message', '').strip()
    ts = l.get('timestamp', '')
    print(f"[{ts}] {msg}")
