# -*- coding: utf-8 -*-
import requests
import json

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
q = """
query GetServiceInstance($envId: String!, $svcId: String!) {
  serviceInstance(environmentId: $envId, serviceId: $svcId) {
    numReplicas
    startCommand
    restartPolicyType
    restartPolicyMaxRetries
  }
}
"""
r = requests.post('https://backboard.railway.app/graphql/v2', json={'query': q, 'variables': {
    'envId': 'dac556ad-8055-4931-9261-1d773fb5242c',
    'svcId': '7b5b4cf2-470f-497d-9c27-b4a8a021635d'
}}, headers=headers)
print(json.dumps(r.json(), indent=2))
