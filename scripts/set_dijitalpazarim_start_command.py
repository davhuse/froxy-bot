# -*- coding: utf-8 -*-
import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

with open('dijitalpazarim_railway_config.json', 'r') as f:
    cfg = json.load(f)

svc_id = cfg['service_id']
env_id = cfg['environment_id']

mutation = """
mutation UpdateServiceInstance($svcId: String!, $envId: String!, $input: ServiceInstanceUpdateInput!) {
  serviceInstanceUpdate(serviceId: $svcId, environmentId: $envId, input: $input)
}
"""

variables = {
    'svcId': svc_id,
    'envId': env_id,
    'input': {
        'startCommand': 'python dijitalpazarim_service.py'
    }
}

r = requests.post(
    'https://backboard.railway.app/graphql/v2',
    json={'query': mutation, 'variables': variables},
    headers=headers,
    timeout=15
)

print("Update startCommand status:", r.status_code)
print("Response:", r.text)
