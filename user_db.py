import hashlib
import urllib.request
import json
import ssl
import base64
import os

API_KEY = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
PROJECT_ID = "bot-2-63772"
# Use the allowed 'reklam' collection directly in the base URL
FIRESTORE_ROOT = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/reklam"

# Simple secret key for XOR encryption
SECRET_KEY = os.environ.get("SaaS_ENCRYPTION_KEY", "habil_secret_key_123!@#")

def encrypt_session(session_str):
    if not session_str:
        return ""
    key_bytes = SECRET_KEY.encode('utf-8')
    data_bytes = session_str.encode('utf-8')
    xor_bytes = bytearray(len(data_bytes))
    for i in range(len(data_bytes)):
        xor_bytes[i] = data_bytes[i] ^ key_bytes[i % len(key_bytes)]
    return base64.b64encode(xor_bytes).decode('utf-8')

def decrypt_session(cipher_str):
    if not cipher_str:
        return ""
    try:
        key_bytes = SECRET_KEY.encode('utf-8')
        xor_bytes = base64.b64decode(cipher_str.encode('utf-8'))
        data_bytes = bytearray(len(xor_bytes))
        for i in range(len(xor_bytes)):
            data_bytes[i] = xor_bytes[i] ^ key_bytes[i % len(key_bytes)]
        return data_bytes.decode('utf-8')
    except Exception:
        return ""

def hash_password(password, salt=None):
    if not salt:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password, stored_hash):
    if not stored_hash or ":" not in stored_hash:
        return False
    salt, hashed = stored_hash.split(":", 1)
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest() == hashed

def _get_doc(doc_id):
    url = f"{FIRESTORE_ROOT}/{doc_id}?key={API_KEY}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
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

def _set_doc(doc_id, fields_dict):
    url = f"{FIRESTORE_ROOT}/{doc_id}?key={API_KEY}"
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
        with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
            return r.status in [200, 201]
    except Exception as e:
        print(f"Firestore error saving to reklam/{doc_id}: {e}")
        return False

# SaaS functions
def register_user(username, password, license_key):
    username_clean = username.strip().lower()
    if not username_clean or not password or not license_key:
        return {"success": False, "message": "Tüm alanları doldurunuz."}
        
    # Check if user already exists
    existing = _get_doc(f"saas_user_{username_clean}")
    if existing:
        return {"success": False, "message": "Bu kullanıcı adı zaten alınmış."}
        
    # Validate License Key
    license_doc = _get_doc(f"saas_license_{license_key.strip()}")
    if not license_doc:
        return {"success": False, "message": "Geçersiz lisans anahtarı."}
        
    if license_doc.get("claimed", False):
        return {"success": False, "message": "Bu lisans anahtarı zaten kullanılmış."}
        
    # Create user
    pw_hash = hash_password(password)
    user_data = {
        "username": username_clean,
        "password_hash": pw_hash,
        "license_key": license_key.strip(),
        "created_at": int(os.environ.get("CURRENT_TIMESTAMP", 0))
    }
    
    if not _set_doc(f"saas_user_{username_clean}", user_data):
        return {"success": False, "message": "Kullanıcı oluşturulurken veritabanı hatası oluştu."}
        
    # Mark license as claimed
    license_doc["claimed"] = True
    license_doc["claimed_by"] = username_clean
    _set_doc(f"saas_license_{license_key.strip()}", license_doc)
    
    # Initialize default config for new user
    default_config = {
        "bot_token": "",
        "admin_id": 0,
        "ad_string_session": "",
        "ad_string_session2": "",
        "ad_string_session3": "",
        "ad_sleep_min": 600,
        "ad_sleep_max": 1200,
        "send_images": False,
        "ad_bot_running": False,
        "spacing_cooldown_minutes": 20
    }
    save_user_config(username_clean, default_config)
    
    return {"success": True, "message": "Kayıt işlemi başarıyla tamamlandı!"}

def login_user(username, password):
    username_clean = username.strip().lower()
    user_doc = _get_doc(f"saas_user_{username_clean}")
    if not user_doc:
        return {"success": False, "message": "Kullanıcı bulunamadı."}
        
    if not verify_password(password, user_doc.get("password_hash")):
        return {"success": False, "message": "Hatalı şifre."}
        
    return {"success": True, "user_id": username_clean}

def get_user_config(user_id):
    cfg = _get_doc(f"saas_config_{user_id}")
    if not cfg:
        return {}
    # Decrypt string sessions
    cfg["ad_string_session"] = decrypt_session(cfg.get("ad_string_session", ""))
    cfg["ad_string_session2"] = decrypt_session(cfg.get("ad_string_session2", ""))
    cfg["ad_string_session3"] = decrypt_session(cfg.get("ad_string_session3", ""))
    return cfg

def save_user_config(user_id, config_dict):
    # Encrypt sensitive tokens before saving
    data = config_dict.copy()
    data["ad_string_session"] = encrypt_session(data.get("ad_string_session", ""))
    data["ad_string_session2"] = encrypt_session(data.get("ad_string_session2", ""))
    data["ad_string_session3"] = encrypt_session(data.get("ad_string_session3", ""))
    return _set_doc(f"saas_config_{user_id}", data)

# Generate a new license key (for admin use)
def create_license(license_key, duration_days=30):
    import time
    labels = {
        1: "1 Günlük",
        3: "3 Günlük",
        7: "1 Haftalık",
        30: "1 Aylık",
        90: "3 Aylık",
        3650: "Sınırsız"
    }
    label = labels.get(duration_days, f"{duration_days} Günlük")
    
    data = {
        "key": license_key,
        "duration_days": duration_days,
        "duration_label": label,
        "claimed": False,
        "claimed_by": "",
        "created_at": int(time.time())
    }
    return _set_doc(f"saas_license_{license_key}", data)

def delete_license(license_key):
    url = f"{FIRESTORE_ROOT}/saas_license_{license_key}?key={API_KEY}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, method="DELETE")
        with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
            return r.status in [200, 204]
    except Exception as e:
        print(f"Firestore error deleting license: {e}")
        return False

def get_all_licenses():
    url = f"{FIRESTORE_ROOT}?key={API_KEY}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            data = json.loads(r.read().decode('utf-8'))
            documents = data.get("documents", [])
            licenses = []
            for doc in documents:
                name = doc.get("name", "")
                doc_id = name.split("/")[-1]
                if doc_id.startswith("saas_license_"):
                    fields = doc.get("fields", {})
                    res = {}
                    for k, v in fields.items():
                        if "stringValue" in v:
                            res[k] = v["stringValue"]
                        elif "integerValue" in v:
                            res[k] = int(v["integerValue"])
                        elif "booleanValue" in v:
                            res[k] = v["booleanValue"]
                    licenses.append(res)
            return licenses
    except Exception as e:
        print(f"Error listing all licenses from Firestore: {e}")
        return []

def get_all_user_configs():
    url = f"{FIRESTORE_ROOT}?key={API_KEY}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            data = json.loads(r.read().decode('utf-8'))
            documents = data.get("documents", [])
            configs = {}
            for doc in documents:
                name = doc.get("name", "")
                doc_id = name.split("/")[-1]
                if doc_id.startswith("saas_config_"):
                    user_id = doc_id[len("saas_config_"):]
                    fields = doc.get("fields", {})
                    res = {}
                    for k, v in fields.items():
                        if "stringValue" in v:
                            res[k] = v["stringValue"]
                        elif "integerValue" in v:
                            res[k] = int(v["integerValue"])
                        elif "booleanValue" in v:
                            res[k] = v["booleanValue"]
                    # Decrypt sensitive values
                    res["ad_string_session"] = decrypt_session(res.get("ad_string_session", ""))
                    res["ad_string_session2"] = decrypt_session(res.get("ad_string_session2", ""))
                    res["ad_string_session3"] = decrypt_session(res.get("ad_string_session3", ""))
                    configs[user_id] = res
            return configs
    except Exception as e:
        print(f"Error listing all configs from Firestore: {e}")
        return {}
