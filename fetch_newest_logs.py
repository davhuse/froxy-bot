import requests
import json
import sys
from datetime import datetime, timezone

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
sys.stdout.reconfigure(encoding='utf-8')

ENV_ID = '6ea40a3d-d7cc-4675-a593-29f6db038de1'

q = '''
query GetRecentLogs($envId: String!, $anchorDate: String, $afterLimit: Int) {
  environmentLogs(environmentId: $envId, anchorDate: $anchorDate, afterLimit: $afterLimit) {
    message
    timestamp
    severity
  }
}
'''
now_iso = datetime.now(timezone.utc).isoformat()
q_now = '''
query GetRecentLogs($envId: String!, $anchorDate: String, $beforeLimit: Int) {
  environmentLogs(environmentId: $envId, anchorDate: $anchorDate, beforeLimit: $beforeLimit) {
    message
    timestamp
    severity
  }
}
'''
r = requests.post(url, json={'query': q_now, 'variables': {'envId': ENV_ID, 'anchorDate': now_iso, 'beforeLimit': 60}}, headers=headers)
logs = r.json().get('data', {}).get('environmentLogs', [])
print(f"Retrieved {len(logs)} logs:")
for l in logs[-50:]:
    msg = l.get('message', '').strip()
    ts = l.get('timestamp', '')
    print(f"[{ts}] {msg}")
