# -*- coding: utf-8 -*-
import requests
import json

BOT_TOKEN = '8753762842:AAHH_uLartBSDD7hJ2ikwaDtoCYpWMziv9g'
webhook_url = 'https://dijital-pazarim-service-production.up.railway.app/api/telegram-webhook'

res = requests.post(
    f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook',
    json={
        'url': webhook_url,
        'drop_pending_updates': True,
        'allowed_updates': ['message', 'callback_query']
    },
    timeout=15
)
print('setWebhook result:', json.dumps(res.json(), indent=2))

res_info = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo', timeout=10)
print('getWebhookInfo result:', json.dumps(res_info.json(), indent=2))
