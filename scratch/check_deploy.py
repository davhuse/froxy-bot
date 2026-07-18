import urllib.request
import json
import ssl

ctx = ssl._create_unverified_context()
url = "https://api.render.com/v1/services/srv-d99tvf8k1i2s73eq3q7g/deploys?limit=5"
req = urllib.request.Request(url)
req.add_header("Authorization", "Bearer rnd_uSYeDJkX0xrcNfgo2BP7Tu3dRvuE")
req.add_header("Accept", "application/json")

try:
    with urllib.request.urlopen(req, context=ctx) as r:
        data = json.loads(r.read().decode("utf-8"))
        print("=== Render Deploys ===")
        for d in data:
            deploy = d.get("deploy", d)
            commit_msg = deploy.get("commit", {}).get("message", "N/A")
            print(f"Deploy ID: {deploy.get('id')} | Status: {deploy.get('status')} | Created: {deploy.get('createdAt')} | Commit: {commit_msg}")
except Exception as e:
    print("Error:", e)
