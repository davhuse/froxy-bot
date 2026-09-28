import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

q = """
query GetDeploy($id: String!) {
  deployment(id: $id) {
    id
    status
    createdAt
    updatedAt
  }
}
"""
r = requests.post(url, json={'query': q, 'variables': {'id': 'a0cfe3ad-b570-4f93-b6d4-d5583b25cbfa'}}, headers=headers)
print(r.json())
