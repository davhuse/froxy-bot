import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
WORKSPACE_ID = 'a1d9b117-462a-4a18-9850-cd11379cde08'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = '''
mutation CreateProj($wsId: String!) {
  projectCreate(input: {
    name: "froxy-jarvis-ecosystem",
    description: "Multi-bot SaaS ecosystem (JarvisCraft, Froxy, KeyVadi, LisansArena)",
    workspaceId: $wsId
  }) {
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
'''
r = requests.post(url, json={'query': q, 'variables': {'wsId': WORKSPACE_ID}}, headers=headers)
print("Project Create Result:", json.dumps(r.json(), indent=2))
