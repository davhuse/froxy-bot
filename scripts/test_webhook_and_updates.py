# -*- coding: utf-8 -*-
import requests

BOT_TOKEN = '8753762842:AAHH_uLartBSDD7hJ2ikwaDtoCYpWMziv9g'
r_del = requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook', json={'drop_pending_updates': True}, timeout=10)
print('deleteWebhook:', r_del.json())

r_upd = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?timeout=1', timeout=10)
print('getUpdates:', r_upd.json())
