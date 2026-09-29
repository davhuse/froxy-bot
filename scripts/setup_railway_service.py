# -*- coding: utf-8 -*-
"""Configure environment variables and public domain on new Railway service."""

import requests
import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from check_shopier_jwts import vars as shopier_vars

sys.stdout.reconfigure(encoding='utf-8')

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

with open('dijitalpazarim_railway_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

proj_id = cfg['project_id']
env_id = cfg['environment_id']
svc_id = cfg['service_id']

# 1. Generate Public Domain
print("1. Generating public domain for service...")
mutation_domain = """
mutation CreateDomain($input: ServiceDomainCreateInput!) {
  serviceDomainCreate(input: $input) {
    domain
  }
}
"""
r_domain = requests.post(
    'https://backboard.railway.app/graphql/v2',
    json={'query': mutation_domain, 'variables': {'input': {'environmentId': env_id, 'serviceId': svc_id}}},
    headers=headers,
    timeout=15
)
domain_data = r_domain.json()
print("Domain creation status:", r_domain.status_code)
print("Domain response:", json.dumps(domain_data, indent=2))

domain = domain_data.get('data', {}).get('serviceDomainCreate', {}).get('domain')
if domain:
    cfg['domain'] = domain
    print(f"\nGenerated Public Domain: https://{domain}")

# 2. Set Environment Variables
print("\n2. Setting environment variables...")
mutation_vars = """
mutation UpsertVars($input: VariableCollectionUpsertInput!) {
  variableCollectionUpsert(input: $input)
}
"""

jarvis_token = shopier_vars.get('SHOPIER_JARVIS_ACCESS_TOKEN')

variables_to_set = {
    'DIJITALPAZARIM_BOT_TOKEN': '8753762842:AAHH_uLartBSDD7hJ2ikwaDtoCYpWMziv9g',
    'SHOPIER_JARVIS_ACCESS_TOKEN': jarvis_token,
    'FLASK_SECRET_KEY': 'dijitalpazarim_prod_secret_8753762842_v1',
    'PORT': '5000',
    'PYTHONUNBUFFERED': '1'
}

if domain:
    variables_to_set['PUBLIC_BASE_URL'] = f"https://{domain}"

vars_input = {
    'projectId': proj_id,
    'environmentId': env_id,
    'serviceId': svc_id,
    'variables': variables_to_set
}

r_vars = requests.post(
    'https://backboard.railway.app/graphql/v2',
    json={'query': mutation_vars, 'variables': {'input': vars_input}},
    headers=headers,
    timeout=15
)
print("Vars status:", r_vars.status_code)
print("Vars response:", r_vars.text)

# Save updated config
with open('dijitalpazarim_railway_config.json', 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2)

print("\nFinished domain & environment setup!")
