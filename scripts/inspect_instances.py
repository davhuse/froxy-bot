import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

def run_query(q, vars=None):
    r = requests.post('https://backboard.railway.app/graphql/v2', json={'query': q, 'variables': vars or {}}, headers=headers)
    return r.json()

q = """
query GetServiceInstance($envId: String!, $svcId: String!) {
  serviceInstance(environmentId: $envId, serviceId: $svcId) {
    startCommand
    restartPolicyType
  }
}
"""

main_env = "f5d137b4-35ce-49e0-8fa4-5264b3ef86eb"
main_svc = "2cc6c23b-25e3-4d37-9cf0-8db3575eca1f"
res_main = run_query(q, {"envId": main_env, "svcId": main_svc})
print("Main Service Instance:", json.dumps(res_main, indent=2))

dp_cfg = json.load(open('dijitalpazarim_railway_config.json'))
res_dp = run_query(q, {"envId": dp_cfg['environment_id'], "svcId": dp_cfg['service_id']})
print("DP Service Instance:", json.dumps(res_dp, indent=2))
