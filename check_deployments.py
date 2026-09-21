import urllib.request
import json

TOKEN = "cb8db854-3ede-42e7-af5a-8d896d8c7cb2"
URL = "https://backboard.railway.app/graphql/v2"

query = """
query {
  service(id: "2cc6c23b-25e3-4d37-9cf0-8db3575eca1f") {
    deployments(first: 6) {
      edges {
        node {
          id
          status
          createdAt
        }
      }
    }
  }
}
"""

req = urllib.request.Request(
    URL,
    data=json.dumps({"query": query}).encode("utf-8"),
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(json.dumps(data, indent=2))
except Exception as e:
    print("Error:", e)
