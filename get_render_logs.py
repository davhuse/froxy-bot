import json
import os
import urllib.request

req = urllib.request.Request(
    'https://api.render.com/v1/services/srv-da34gve7bikc7395idu0/logs?limit=80',
    headers={'Authorization': f"Bearer {os.environ['RENDER_API_KEY']}", 'Accept': 'application/json'}
)
try:
    with urllib.request.urlopen(req) as r:
        logs = json.loads(r.read().decode('utf-8'))
        for entry in reversed(logs):
            msg = entry.get('message', '')
            ts = entry.get('timestamp', '')
            print(f"[{ts}] {msg}")
except Exception as e:
    print('Error:', e)
