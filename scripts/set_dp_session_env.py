import json
import requests

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
cfg = json.load(open('dijitalpazarim_railway_config.json'))
session = open('dijitalpazarim_session_string.txt', encoding='utf-8').read().strip()
q = """
mutation SetVars($envId: String!, $projId: String!, $svcId: String!, $vars: EnvironmentVariables!) {
  variableCollectionUpsert(input: {environmentId: $envId, projectId: $projId, serviceId: $svcId, variables: $vars, skipDeploys: true})
}
"""
r = requests.post('https://backboard.railway.app/graphql/v2',
                  json={'query': q, 'variables': {'envId': cfg['environment_id'], 'projId': cfg['project_id'],
                                                  'svcId': cfg['service_id'],
                                                  'vars': {'AD_STRING_SESSION_DIJITALPAZARIM': session}}},
                  headers={'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}, timeout=15)
print('Upsert:', r.json())
