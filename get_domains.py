import requests
import json

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
q = '''
query GetServiceDomains($serviceId: String!) {
  service(id: $serviceId) {
    name
    serviceInstances {
      edges {
        node {
          domains {
            serviceDomains {
              domain
            }
            customDomains {
              domain
            }
          }
        }
      }
    }
  }
}
'''
r = requests.post(url, json={'query': q, 'variables': {'serviceId': '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'}}, headers=headers, timeout=10)
print(json.dumps(r.json(), indent=2))
