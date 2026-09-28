import urllib.request
import json
import ssl

ctx = ssl._create_unverified_context()
domains = [
    'https://bot-service-production-9d74.up.railway.app',
    'https://bot-service-production-1a56.up.railway.app'
]

for d in domains:
    print(f"Testing {d}...")
    try:
        req = urllib.request.Request(f"{d}/health")
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            body = r.read().decode('utf-8', errors='replace')
            print(f"  /health: {r.status} {body[:120]}")
    except Exception as e:
        print(f"  /health error: {e}")
        
    try:
        req = urllib.request.Request(f"{d}/api/status")
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            status_data = json.loads(r.read().decode('utf-8', errors='replace'))
            print("  /api/status:")
            print("    bot_runtime_enabled:", status_data.get("bot_runtime_enabled"))
            print("    worker_running:", status_data.get("worker_running"))
            print("    keyvadi_support:", status_data.get("keyvadi_support"))
            print("    support_running:", status_data.get("support_running"))
            print("    accounts:", list(status_data.get("ad_accounts", {}).keys()))
    except Exception as e:
        print(f"  /api/status error: {e}")
