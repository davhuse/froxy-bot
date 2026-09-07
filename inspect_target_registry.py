import json
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

api_key = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
project = "bot-2-63772"
url = f"https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents/reklam/target_registry?key={api_key}"

req = urllib.request.Request(url)
with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
    data = json.loads(r.read().decode('utf-8'))
    raw = data.get("fields", {}).get("registry_json", {}).get("stringValue")
    if raw:
        parsed = json.loads(raw)
        print("Candidates in TargetRegistry:")
        candidates = parsed.get("candidates", {})
        print(f"Total candidates: {len(candidates)}")
        for k, v in candidates.items():
            print(f" - @{v.get('username')}: score={v.get('score')} title={v.get('title')} reasons={v.get('reasons')}")
        print("\nApproved in TargetRegistry:")
        approved = parsed.get("approved", {})
        print(f"Total approved: {len(approved)}")
    else:
        print("No registry_json field found")
