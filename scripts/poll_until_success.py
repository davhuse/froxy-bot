# -*- coding: utf-8 -*-
import time
import requests
import sys

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
q = """
query GetDeploy($id: String!) {
  deployment(id: $id) {
    id
    status
  }
}
"""

main_id = '66686684-3380-43bf-8855-7656af97325e'
dp_id = '7d97a11d-ceae-460d-bc15-109e53f78837'

for i in range(12): # up to 2 minutes
    time.sleep(10)
    m = requests.post('https://backboard.railway.app/graphql/v2', json={'query': q, 'variables': {'id': main_id}}, headers=headers).json().get('data', {}).get('deployment', {}).get('status')
    d = requests.post('https://backboard.railway.app/graphql/v2', json={'query': q, 'variables': {'id': dp_id}}, headers=headers).json().get('data', {}).get('deployment', {}).get('status')
    print(f"Poll {i+1} ({round((i+1)*10)}s): Main: {m} | DP: {d}")
    if m == 'SUCCESS' and d == 'SUCCESS':
        print("Both deployments reached SUCCESS!")
        break
    if m in ['FAILED', 'CRASHED'] or d in ['FAILED', 'CRASHED']:
        print("A deployment failed!")
        break
