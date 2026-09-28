import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

base = 'https://bot-service-production-9d74.up.railway.app'
token = 'VOJVbVkVHQBw5J3zI8vQeW2zP5iK6uY9'
headers = {'X-Admin-Token': token}

r = requests.get(f'{base}/api/tickets', headers=headers)
tickets = r.json().get('tickets', [])

print(f"Total tickets: {len(tickets)}")
for t in tickets[-25:]:
    ts = t.get('timestamp')
    b = t.get('bot_type')
    u = t.get('username') or t.get('user_id')
    m = t.get('message', '').strip()
    print(f"[{ts}] [{b}] [{u}]: {m}")
