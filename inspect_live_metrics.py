import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

base = 'https://bot-service-production-9d74.up.railway.app'
token = 'VOJVbVkVHQBw5J3zI8vQeW2zP5iK6uY9'
headers = {'X-Admin-Token': token}

endpoints = [
    ('/api/sales/summary', 'SALES SUMMARY'),
    ('/api/dm-logs', 'DM LOGS'),
    ('/api/tickets', 'TICKETS'),
    ('/api/account-restrictions', 'ACCOUNT RESTRICTIONS'),
    ('/api/group-status', 'GROUP STATUS'),
]

for ep, label in endpoints:
    print(f"\n==================== {label} ({ep}) ====================")
    try:
        r = requests.get(f"{base}{ep}", headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            if len(formatted) > 1500:
                print(formatted[:1500] + "\n... [TRUNCATED]")
            else:
                print(formatted)
        else:
            print(f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
