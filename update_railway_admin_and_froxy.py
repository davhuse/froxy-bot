import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
PROJECT_ID = '5fa77867-f818-4da3-b9d9-702529879e6f'
ENV_ID = '6ea40a3d-d7cc-4675-a593-29f6db038de1'
SVC_ID = '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

with open("bot_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

cfg["admin_id"] = 7499698483
cfg["admin_ids"] = [7499698483]
cfg["froxy_admin_id"] = 7499698483
cfg["froxy_bot_running"] = False
cfg["lisansarena_bot_token"] = "8971644915:AAESpHgQS5WtAGpCdSI8ACulN9Be9hZ-Dsw"

new_vars = {
    'TELEGRAM_ADMIN_ID': '7499698483',
    'DISABLE_FROXY_AD': 'true',
    'DISABLED_AD_ACCOUNTS': 'froxyonline,froxy',
    'BOT_CONFIG_JSON': json.dumps(cfg),
    'LISANSARENA_BOT_TOKEN': '8971644915:AAESpHgQS5WtAGpCdSI8ACulN9Be9hZ-Dsw',
    'LISANSARENA_SUPPORT_BOT_TOKEN': '8971644915:AAESpHgQS5WtAGpCdSI8ACulN9Be9hZ-Dsw',
}

q = """
mutation SetVars($envId: String!, $projId: String!, $svcId: String!, $vars: EnvironmentVariables!) {
  variableCollectionUpsert(input: {
    environmentId: $envId,
    projectId: $projId,
    serviceId: $svcId,
    variables: $vars,
    skipDeploys: false
  })
}
"""

r = requests.post(
    url,
    json={
        'query': q,
        'variables': {
            'envId': ENV_ID,
            'projId': PROJECT_ID,
            'svcId': SVC_ID,
            'vars': new_vars,
        }
    },
    headers=headers
)
print('Upsert result:', json.dumps(r.json(), indent=2))
