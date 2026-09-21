import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = """
mutation CreateVolume($input: VolumeCreateInput!) {
  volumeCreate(input: $input) {
    id
    name
  }
}
"""
PROJECT_ID = '5fa77867-f818-4da3-b9d9-702529879e6f'
ENV_ID = '6ea40a3d-d7cc-4675-a593-29f6db038de1'
SVC_ID = '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'

variables = {
  "input": {
    "projectId": PROJECT_ID,
    "environmentId": ENV_ID,
    "serviceId": SVC_ID,
    "mountPath": "/app/data"
  }
}
r = requests.post(url, json={'query': q, 'variables': variables}, headers=headers)
print("Create volume response:", json.dumps(r.json(), indent=2))
