import requests
import json
import sys

BASE = 'https://bot-service-production-9d74.up.railway.app'
sys.stdout.reconfigure(encoding='utf-8')

# Check if PANEL_ADMIN_TOKEN is needed
from check_shopier_jwts import vars
admin_token = vars.get('PANEL_ADMIN_TOKEN', '')
headers = {}
if admin_token:
    headers['X-Admin-Token'] = admin_token

print("=== 1. Checking /api/status ===")
try:
    r = requests.get(f"{BASE}/api/status", headers=headers, timeout=10)
    print(f"Status ({r.status_code}):", json.dumps(r.json(), indent=2)[:500], "...")
except Exception as e:
    print("Status error:", e)

endpoints = [
    ('/api/logs', 'Reklam Botu (otomatik_katil.py) Logs'),
    ('/api/support/logs', 'KeyVadi Destek Botu Logs'),
    ('/api/froxy/logs', 'Froxy AI Botu Logs'),
    ('/api/lisansarena/logs', 'LisansArena Botu Logs'),
    ('/api/jarvis/logs', 'Jarvis Botu Logs'),
    ('/api/dm-logs', 'DM Logs')
]

for ep, desc in endpoints:
    print(f"\n=== Checking {desc} ({ep}) ===")
    try:
        r = requests.get(f"{BASE}{ep}", headers=headers, timeout=10)
        print(f"HTTP {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            lines = data.get('logs', []) if isinstance(data, dict) else data
            if isinstance(lines, list):
                print(f"Total lines: {len(lines)}")
                print("Last 15 lines:")
                for line in lines[-15:]:
                    print("  ", str(line).strip())
            else:
                print(str(lines)[:300])
        else:
            print("Response:", r.text[:300])
    except Exception as e:
        print(f"Error calling {ep}:", e)
