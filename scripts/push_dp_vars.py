# -*- coding: utf-8 -*-
"""Set session string and bot tokens on Railway for Dijital Pazarım."""

import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

with open('dijitalpazarim_railway_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

with open('dijitalpazarim_session_string.txt', 'r', encoding='utf-8') as f:
    session_str = f.read().strip()

new_vars = {
    'AD_STRING_SESSION_DIJITALPAZARIM': session_str,
    'DIJITALPAZARIM_BOT_TOKEN': '8753762842:AAHH_uLartBSDD7hJ2ikwaDtoCYpWMziv9g',
    'TELEGRAM_API_ID': '31076280',
    'TELEGRAM_API_HASH': '7ba4072dcf0a05a7ccf80e570866b6d8',
    'PUBLIC_BASE_URL': 'https://dijital-pazarim-service-production.up.railway.app',
    'PYTHONUNBUFFERED': '1'
}

mutation = """
mutation UpsertVars($input: VariableCollectionUpsertInput!) {
  variableCollectionUpsert(input: $input)
}
"""

vars_input = {
    'projectId': cfg['project_id'],
    'environmentId': cfg['environment_id'],
    'serviceId': cfg['service_id'],
    'variables': new_vars
}

r = requests.post(
    'https://backboard.railway.app/graphql/v2',
    json={'query': mutation, 'variables': {'input': vars_input}},
    headers=headers,
    timeout=15
)

print("Vars update status:", r.status_code)
print("Response:", r.text)
