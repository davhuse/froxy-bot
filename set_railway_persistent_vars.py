import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
PROJECT_ID = '5fa77867-f818-4da3-b9d9-702529879e6f'
ENV_ID = '6ea40a3d-d7cc-4675-a593-29f6db038de1'
SVC_ID = '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = """
mutation SetVars($envId: String!, $projId: String!, $svcId: String!, $vars: EnvironmentVariables!) {
  variableCollectionUpsert(input: {
    environmentId: $envId,
    projectId: $projId,
    serviceId: $svcId,
    variables: $vars,
    skipDeploys: true
  })
}
"""
new_vars = {
    'PERSISTENT_DATA_DIR': '/app/data',
    'BLAST_CHECKPOINT_SQLITE_PATH': '/app/data/blast_checkpoint_backup.db',
    'BLAST_CHECKPOINT_FILE': '/app/data/blast_checkpoint_v3.json',
    'RENDER_EXTERNAL_URL': 'https://bot-service-production-9d74.up.railway.app',
    'PUBLIC_BASE_URL': 'https://bot-service-production-9d74.up.railway.app',
    'LISANSARENA_TOPUP_MEDIA_URL': 'https://bot-service-production-9d74.up.railway.app/la/app/assets/lisansarena_logo.png'
}
r = requests.post(url, json={'query': q, 'variables': {'envId': ENV_ID, 'projId': PROJECT_ID, 'svcId': SVC_ID, 'vars': new_vars}}, headers=headers)
print('Upsert result:', json.dumps(r.json(), indent=2))
