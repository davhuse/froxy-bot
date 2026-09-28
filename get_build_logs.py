import requests
import json
import sys

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
sys.stdout.reconfigure(encoding='utf-8')

q = '''
query GetBuildLogs($id: String!) {
  buildLogs(deploymentId: $id, limit: 15) {
    message
  }
}
'''
r = requests.post(url, json={'query': q, 'variables': {'id': 'a0cfe3ad-e37f-4256-9406-52ddb476f201'}}, headers=headers)
logs = r.json().get('data', {}).get('buildLogs', []) or []
for l in logs[-15:]:
    print(l.get('message', '').strip())
