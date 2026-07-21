import urllib.request
import urllib.error
import json
import ssl
import sys

sys.stdout.reconfigure(encoding='utf-8')

API_KEY = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
PROJECT_ID = "bot-2-63772"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/reklam?key={API_KEY}"

ctx = ssl._create_unverified_context()

try:
    req = urllib.request.Request(BASE_URL)
    with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
        data = json.loads(r.read().decode('utf-8'))
        documents = data.get("documents", [])
        
        found = False
        for doc in documents:
            name = doc.get("name", "")
            doc_id = name.split("/")[-1]
            fields = doc.get("fields", {})
            doc_str = json.dumps(fields, ensure_ascii=False)
            
            if "islamix" in doc_str.lower():
                print(f"Found 'islamix' in Document ID: {doc_id}")
                print(f"  Fields: {fields}")
                found = True
                
        if not found:
            print("No document in Firestore contains 'islamix'.")
            
except Exception as e:
    print(f"Error querying Firestore: {e}")
