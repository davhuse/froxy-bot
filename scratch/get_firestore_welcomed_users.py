import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

API_KEY    = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
PROJECT_ID = "bot-2-63772"
URL        = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/reklam/state?key={API_KEY}"

try:
    req = urllib.request.Request(URL)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        fields = json.loads(r.read().decode('utf-8')).get("fields", {})
        welcomed = fields.get("welcomed_users_list", {}).get("stringValue", "")
        print("Welcomed users in Firestore:")
        print(welcomed)
except Exception as e:
    print(f"Error: {e}")
