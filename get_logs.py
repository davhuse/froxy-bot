import requests
import json
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
DEPLOY_ID = 'f37ed5c9-f5e9-40a7-b3dc-b5642fe6c1db'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = '''
query GetLogs($id: String!) {
  deploymentLogs(deploymentId: $id, limit: 50) {
    message
    timestamp
  }
}
'''
r = requests.post(url, json={'query': q, 'variables': {'id': DEPLOY_ID}}, headers=headers)
try:
    data = r.json()
    logs = data.get('data', {}).get('deploymentLogs', [])
    print(f"Total log lines: {len(logs)}")
    for l in logs:
        print(l.get('timestamp'), l.get('message'))
except Exception as e:
    print(r.text)
