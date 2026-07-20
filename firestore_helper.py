import urllib.request
import urllib.error
import json
import ssl

API_KEY = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
PROJECT_ID = "bot-2-63772"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/reklam"
COMMIT_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents:commit"
DOCUMENT_PREFIX = f"projects/{PROJECT_ID}/databases/(default)/documents/reklam"

def get_document(doc_id):
    url = f"{BASE_URL}/{doc_id}?key={API_KEY}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            data = json.loads(r.read().decode('utf-8'))
            fields = data.get("fields", {})
            res = {}
            for k, v in fields.items():
                if "stringValue" in v:
                    res[k] = v["stringValue"]
                elif "integerValue" in v:
                    res[k] = int(v["integerValue"])
                elif "booleanValue" in v:
                    res[k] = v["booleanValue"]
            return res
    except Exception:
        return None

def set_document(doc_id, fields_dict):
    url = f"{BASE_URL}/{doc_id}?key={API_KEY}"
    ctx = ssl._create_unverified_context()
    
    fields = {}
    for k, v in fields_dict.items():
        if isinstance(v, bool):
            fields[k] = {"booleanValue": v}
        elif isinstance(v, int):
            fields[k] = {"integerValue": str(v)}
        else:
            fields[k] = {"stringValue": str(v)}
            
    body = json.dumps({"fields": fields}).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=body, method="PATCH")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            return r.status in [200, 201]
    except Exception as e:
        print(f"Firestore save error for doc {doc_id}: {e}")
        return False

def delete_document(doc_id):
    url = f"{BASE_URL}/{doc_id}?key={API_KEY}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, method="DELETE")
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            return r.status in [200, 204]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return True
        print(f"Firestore delete error for doc {doc_id}: HTTP {e.code}")
        return False
    except Exception as e:
        print(f"Firestore delete error for doc {doc_id}: {type(e).__name__}")
        return False

def claim_document(doc_id, fields_dict=None):
    """Atomically create a document; False means another worker already claimed it."""
    url = f"{COMMIT_URL}?key={API_KEY}"
    ctx = ssl._create_unverified_context()
    fields = {}
    for k, v in (fields_dict or {}).items():
        if isinstance(v, bool):
            fields[k] = {"booleanValue": v}
        elif isinstance(v, int):
            fields[k] = {"integerValue": str(v)}
        else:
            fields[k] = {"stringValue": str(v)}
    body = json.dumps({"writes": [{
        "update": {"name": f"{DOCUMENT_PREFIX}/{doc_id}", "fields": fields},
        "currentDocument": {"exists": False}
    }]}).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            return r.status in [200, 201]
    except urllib.error.HTTPError as e:
        if e.code in (400, 409):
            return False
        print(f"Firestore claim error for doc {doc_id}: HTTP {e.code}")
        return None
    except Exception as e:
        print(f"Firestore claim error for doc {doc_id}: {type(e).__name__}")
        return None
