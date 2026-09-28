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
vars = r.json().get('data', {}).get('variables', {})
token = vars.get('PANEL_ADMIN_TOKEN')
print('PANEL_ADMIN_TOKEN exists:', bool(token))

r_logs = requests.get('https://bot-service-production-9d74.up.railway.app/api/logs', headers={'X-Admin-Token': token}, timeout=15)
print('Logs status:', r_logs.status_code)
try:
    data = r_logs.json()
    logs_text = data.get('logs', r_logs.text)
except:
    logs_text = r_logs.text

if isinstance(logs_text, list):
    lines = logs_text
else:
    lines = logs_text.splitlines()
print(f'Total log lines: {len(lines)}')
print('\nLast 30 lines:')
for line in lines[-30:]:
    print(line)

matched = [line for line in lines if '8777291796' in line or 'Windows 11' in line or 'DM Alindi' in line or 'DM' in line]
print(f'\nMatched DM lines ({len(matched)}):')
for m in matched[-20:]:
    print(m)
