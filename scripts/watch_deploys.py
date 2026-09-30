import requests
import json
import time

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

def get_latest_deployment(svc_id):
    q = """
    query GetDeployments($svcId: String!) {
      service(id: $svcId) {
        name
        deployments(first: 1) {
          edges {
            node {
              id
              status
              createdAt
              meta
            }
          }
        }
      }
    }
    """
    res = requests.post(
        'https://backboard.railway.app/graphql/v2',
        json={'query': q, 'variables': {'svcId': svc_id}},
        headers=headers,
        timeout=10
    ).json()
    try:
        node = res['data']['service']['deployments']['edges'][0]['node']
        return node['id'], node['status'], node['createdAt'], node.get('meta', {})
    except Exception as e:
        return None, str(e), None, {}

main_svc_id = "2cc6c23b-25e3-4d37-9cf0-8db3575eca1f"
dp_svc_id = "7b5b4cf2-470f-497d-9c27-b4a8a021635d"

print("Watching deployments...")
for i in range(24): # up to 2 minutes
    main_id, main_status, main_time, main_meta = get_latest_deployment(main_svc_id)
    dp_id, dp_status, dp_time, dp_meta = get_latest_deployment(dp_svc_id)
    
    print(f"[{i*5}s] Main: {main_status} ({main_id}) | DP: {dp_status} ({dp_id})")
    
    if main_status in ['SUCCESS', 'FAILED', 'CRASHED'] and dp_status in ['SUCCESS', 'FAILED', 'CRASHED']:
        break
    time.sleep(5)

print("\n--- FINAL STATUS ---")
print(f"Main ({main_svc_id}): {main_status}")
print(f"DP ({dp_svc_id}): {dp_status}")
