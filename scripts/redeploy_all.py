import requests
import json
import time

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

def run_query(query, variables=None):
    res = requests.post(
        'https://backboard.railway.app/graphql/v2',
        json={'query': query, 'variables': variables or {}},
        headers=headers,
        timeout=15
    )
    return res.json()

# 1. Main Project
print("Querying Main Project...")
main_proj = run_query("""
query {
  project(id: "5fa77867-f818-4da3-b9d9-702529879e6f") {
    name
    environments {
      edges {
        node {
          id
          name
        }
      }
    }
    services {
      edges {
        node {
          id
          name
        }
      }
    }
  }
}
""")
print(json.dumps(main_proj, indent=2))

main_env_id = main_proj['data']['project']['environments']['edges'][0]['node']['id']
main_svc_id = "2cc6c23b-25e3-4d37-9cf0-8db3575eca1f"

# 2. Deploy latest commit on Main Server (bot-service)
print(f"Deploying latest commit on Main Server ({main_svc_id}) in env {main_env_id}...")
dep_main = run_query("""
mutation DeployLatest($envId: String!, $svcId: String!) {
  serviceInstanceDeploy(environmentId: $envId, serviceId: $svcId, latestCommit: true)
}
""", {'envId': main_env_id, 'svcId': main_svc_id})
print("Main deploy response:", dep_main)

# 3. Deploy latest commit on Dijital Pazarim Server
dp_cfg = json.load(open('dijitalpazarim_railway_config.json'))
print(f"Deploying latest commit on Dijital Pazarim Server ({dp_cfg['service_id']}) in env {dp_cfg['environment_id']}...")
dep_dp = run_query("""
mutation DeployLatest($envId: String!, $svcId: String!) {
  serviceInstanceDeploy(environmentId: $envId, serviceId: $svcId, latestCommit: true)
}
""", {'envId': dp_cfg['environment_id'], 'svcId': dp_cfg['service_id']})
print("Dijital Pazarim deploy response:", dep_dp)
