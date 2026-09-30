# -*- coding: utf-8 -*-
import requests
import time

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = """
query GetDeploy($id: String!) {
  deployment(id: $id) {
    id
    status
    createdAt
  }
}
"""

main_dep_id = "66686684-3380-43bf-8855-7656af97325e"
dp_dep_id = "7d97a11d-ceae-460d-bc15-109e53f78837"

def get_status(dep_id):
    r = requests.post('https://backboard.railway.app/graphql/v2', json={'query': q, 'variables': {'id': dep_id}}, headers=headers, timeout=10)
    data = r.json()
    dep = data.get('data', {}).get('deployment')
    return dep['status'] if dep else 'UNKNOWN'

print(f"Monitoring deploys:\n  Main: {main_dep_id}\n  DP:   {dp_dep_id}\n")

for i in range(30): # up to 2.5 minutes
    m_st = get_status(main_dep_id)
    d_st = get_status(dp_dep_id)
    print(f"[{i*5:3}s] Main: {m_st:10} | DP: {d_st:10}")
    if m_st in ['SUCCESS', 'FAILED', 'CRASHED'] and d_st in ['SUCCESS', 'FAILED', 'CRASHED']:
        break
    time.sleep(5)

print("\nFinal Status:")
print(f"  Main Deploy: {m_st}")
print(f"  DP Deploy:   {d_st}")
