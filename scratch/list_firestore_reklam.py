import urllib.request
import json
import ssl

API_KEY = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
PROJECT_ID = "bot-2-63772"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/reklam?key={API_KEY}"

print("Fetching Firestore reklam documents...")
ctx = ssl._create_unverified_context()
try:
    req = urllib.request.Request(BASE_URL)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        data = json.loads(r.read().decode('utf-8'))
        documents = data.get("documents", [])
        print(f"Found {len(documents)} documents:")
        for doc in documents:
            name = doc.get("name", "").split("/")[-1]
            fields = doc.get("fields", {})
            cleaned = {}
            for k, v in fields.items():
                val_type = list(v.keys())[0]
                val = v[val_type]
                if "key" in k.lower() or "token" in k.lower() or "secret" in k.lower() or "password" in k.lower() or "session" in k.lower():
                    cleaned[k] = "REDACTED"
                else:
                    cleaned[k] = val
            print(f"- ID: {name}")
            print(f"  Data: {cleaned}")
            print("-" * 50)
except Exception as e:
    print("Error listing Firestore:", e)
