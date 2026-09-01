import os
import urllib.request, json

req = urllib.request.Request(
    'https://api.render.com/v1/services/srv-da34gve7bikc7395idu0/env-vars',
    headers={'Authorization': f"Bearer {os.environ['RENDER_API_KEY']}", 'Accept': 'application/json'}
)
with urllib.request.urlopen(req) as r:
    vars_list = json.loads(r.read().decode('utf-8'))
    for v in vars_list:
        key = v.get('envVar', {}).get('key')
        configured = bool(v.get('envVar', {}).get('value', ''))
        print(f'{key}: {"configured" if configured else "empty"}')
