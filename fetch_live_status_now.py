import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
q = """
query GetVars($projId: String!, $envId: String!, $svcId: String!) {
  variables(projectId: $projId, environmentId: $envId, serviceId: $svcId)
}
"""
r = requests.post(url, json={'query': q, 'variables': {
    'projId': '5fa77867-f818-4da3-b9d9-702529879e6f',
    'envId': '6ea40a3d-d7cc-4675-a593-29f6db038de1',
    'svcId': '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'
}}, headers=headers)
token = r.json().get('data', {}).get('variables', {}).get('PANEL_ADMIN_TOKEN')

auth_headers = {'X-Admin-Token': token}
base_url = 'https://bot-service-production-9d74.up.railway.app'

try:
    r_status = requests.get(f'{base_url}/api/status', headers=auth_headers, timeout=15)
    print("STATUS:")
    print(json.dumps(r_status.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print('Status error:', e)

try:
    r_logs = requests.get(f'{base_url}/api/logs', headers=auth_headers, timeout=15)
    lines = r_logs.json().get('logs', [])
    print(f"\nLOGS (Total {len(lines)} lines):")
    for l in lines[-40:]:
        print(l)
except Exception as e:
    print('Logs error:', e)
