import urllib.request
import json
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

render_key = 'rnd_4c83vU85zEZ7KOjaS5crYqM4x55G'
srv_id = 'srv-danfkkek1f9s738iq5rg'

print("=== 1. CHECKING RENDER SERVICE ===")
req = urllib.request.Request(
    f'https://api.render.com/v1/services/{srv_id}',
    headers={'Authorization': f'Bearer {render_key}'}
)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print('Service Name:', data.get('name'))
        print('Suspended:', data.get('suspended'))
        print('Service Details:', data.get('serviceDetails', {}))
except Exception as e:
    print('Service details error:', e)

print("\n=== 2. CHECKING DEPLOYS ===")
req_dep = urllib.request.Request(
    f'https://api.render.com/v1/services/{srv_id}/deploys?limit=3',
    headers={'Authorization': f'Bearer {render_key}'}
)
try:
    with urllib.request.urlopen(req_dep) as resp:
        data_dep = json.loads(resp.read().decode())
        for d in data_dep:
            dep = d.get('deploy', {})
            print(f"Deploy ID: {dep.get('id')} | Status: {dep.get('status')} | Created: {dep.get('createdAt')} | Finished: {dep.get('finishedAt')}")
except Exception as e:
    print('Deploy list error:', e)

print("\n=== 3. CHECKING LIVE ENDPOINT ===")
token = 'VOJVbVkVHQBw5J3zI8vQeW2zP5iK6uY9'
headers = {'X-Admin-Token': token}
req_logs = urllib.request.Request('https://froxy-bot-1.onrender.com/api/logs?limit=30', headers=headers)
try:
    with urllib.request.urlopen(req_logs, timeout=12) as resp:
        print('HTTP Status:', resp.status)
        data_logs = json.loads(resp.read().decode())
        logs = data_logs.get('logs', [])
        print(f'Total logs: {len(logs)}')
        for l in logs[-20:]:
            print('  ', l.strip())
except urllib.error.HTTPError as e:
    print(f'Live endpoint HTTPError: {e.code} {e.reason}')
    try:
        print(e.read().decode()[:300])
    except:
        pass
except Exception as e:
    print('Live endpoint error:', e)
