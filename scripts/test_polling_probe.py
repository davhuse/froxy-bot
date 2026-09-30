# -*- coding: utf-8 -*-
import requests
import time

BOT_TOKEN = '8753762842:AAHH_uLartBSDD7hJ2ikwaDtoCYpWMziv9g'

# Reset any webhook
requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook', json={'drop_pending_updates': True}, timeout=10)

session = requests.Session()
for i in range(5):
    try:
        t0 = time.time()
        r = session.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates', params={'timeout': 1}, timeout=10)
        dt = round(time.time() - t0, 2)
        print(f"[{i+1}] Status: {r.status_code} ({dt}s) -> {r.json()}")
    except Exception as e:
        print(f"[{i+1}] Error: {e}")
    time.sleep(2)
