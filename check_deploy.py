import urllib.request
import json
import time

headers = {
    'Authorization': 'Bearer rnd_clV0XeKhgZSRU5gPF8lTrQkBJCps',
    'Accept': 'application/json'
}

for i in range(15):
    try:
        req = urllib.request.Request(
            'https://api.render.com/v1/services/srv-da34gve7bikc7395idu0/deploys?limit=3',
            headers=headers
        )
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode('utf-8'))
            top = data[0]['deploy']
            dep_id = top['id']
            status = top['status']
            msg = top.get('commit', {}).get('message', '')
            print(f"Deploy: {dep_id} | Status: {status} | Message: {msg[:50]}")
            if status == 'live':
                print("==> DEPLOY IS LIVE!")
                break
    except Exception as e:
        print("Error checking deploy:", e)
    time.sleep(10)
