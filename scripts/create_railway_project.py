# -*- coding: utf-8 -*-
"""Create a dedicated Railway project and service for Dijital Pazarım."""

import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

token = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
workspace_id = 'a1d9b117-462a-4a18-9850-cd11379cde08'
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

print("1. Creating Railway project 'dijital-pazarim'...")
mutation_proj = """
mutation CreateProj($input: ProjectCreateInput!) {
  projectCreate(input: $input) {
    id
    name
    environments {
      edges {
        node {
          id
          name
        }
      }
    }
  }
}
"""

r = requests.post(
    'https://backboard.railway.app/graphql/v2',
    json={'query': mutation_proj, 'variables': {'input': {'name': 'dijital-pazarim', 'workspaceId': workspace_id}}},
    headers=headers,
    timeout=15
)

print(f"Status: {r.status_code}")
data = r.json()
print("Response:", json.dumps(data, indent=2))

if 'errors' in data:
    print("Project create error!")
    sys.exit(1)

proj_data = data['data']['projectCreate']
proj_id = proj_data['id']
env_id = proj_data['environments']['edges'][0]['node']['id']
print(f"\nProject created successfully! ID: {proj_id}, Environment ID: {env_id}")

# 2. Create Service connected to GitHub repo 'davhuse/froxy-bot'
print("\n2. Creating service connected to GitHub repo 'davhuse/froxy-bot'...")
mutation_svc = """
mutation CreateService($input: ServiceCreateInput!) {
  serviceCreate(input: $input) {
    id
    name
  }
}
"""
svc_vars = {
    'input': {
        'projectId': proj_id,
        'name': 'dijital-pazarim-service',
        'source': {
            'repo': 'davhuse/froxy-bot'
        }
    }
}
r_svc = requests.post(
    'https://backboard.railway.app/graphql/v2',
    json={'query': mutation_svc, 'variables': svc_vars},
    headers=headers,
    timeout=15
)
print(f"Service status: {r_svc.status_code}")
svc_data = r_svc.json()
print("Service Response:", json.dumps(svc_data, indent=2))

svc_id = svc_data.get('data', {}).get('serviceCreate', {}).get('id')

# Save all details to a config file
details = {
    'project_id': proj_id,
    'environment_id': env_id,
    'service_id': svc_id
}
with open('dijitalpazarim_railway_config.json', 'w', encoding='utf-8') as f:
    json.dump(details, f, indent=2)

print("\nSaved configuration to dijitalpazarim_railway_config.json")
