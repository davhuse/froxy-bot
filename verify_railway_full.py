import requests
import json
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://bot-service-production-9d74.up.railway.app'

print("🔍 [1/5] Testing Mini App HTML...")
r_app = requests.get(f"{BASE}/jarvis/app", timeout=15)
print(f"MiniApp status: {r_app.status_code}, Length: {len(r_app.text)}")
assert r_app.status_code == 200, "Mini App failed to load"
assert "JarvisCraft" in r_app.text, "Brand missing"
assert "https://www.shopier.com/JarvisStore" in r_app.text, "Shopier store link missing"
assert "@JarvisCraft" in r_app.text, "Support link missing"
print("  ✅ Mini App HTML verified with correct branding, Shopier store, and @JarvisCraft support!")

print("\n🔍 [2/5] Testing /api/status...")
r_status = requests.get(f"{BASE}/api/status", timeout=15)
print(f"Status code: {r_status.status_code}")
if r_status.status_code == 200:
    st = r_status.json()
    print("  Bot runtime enabled:", st.get('bot_runtime_enabled'))
    print("  Ad runtime enabled:", st.get('ad_runtime_enabled'))
    print("  Sales bots:", json.dumps(st.get('sales_bots'), indent=2))
    print("  Ad accounts:", list(st.get('ad_accounts', {}).keys()))

print("\n🔍 [3/5] Testing /api/system-checkup...")
r_check = requests.get(f"{BASE}/api/system-checkup", timeout=15)
print(f"Checkup status: {r_check.status_code}")
if r_check.status_code == 200:
    ch = r_check.json()
    print("  Processes:", json.dumps(ch.get('processes'), indent=2))
    print("  Sales bots:", json.dumps(ch.get('sales_bots'), indent=2))

print("\n🔍 [4/5] Testing /api/jarvis/status...")
try:
    r_jstatus = requests.get(f"{BASE}/api/jarvis/status", timeout=15)
    print(f"Jarvis status code: {r_jstatus.status_code}")
    print("  Jarvis info:", json.dumps(r_jstatus.json(), indent=2))
except Exception as e:
    print("  Jarvis status not yet available:", e)

print("\n🔍 [5/5] Testing /api/jarvis/logs...")
try:
    r_jlogs = requests.get(f"{BASE}/api/jarvis/logs", timeout=15)
    print(f"Jarvis logs code: {r_jlogs.status_code}")
    logs = r_jlogs.json().get('logs', [])
    print(f"  Total log lines: {len(logs)}")
    for line in logs[-10:]:
        print("    ", line.strip())
except Exception as e:
    print("  Jarvis logs not yet available:", e)

print("\n🏁 Verification complete.")
