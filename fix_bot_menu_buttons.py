import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

from check_sessions import vars

bot_configs = [
    {
        'name': 'KeyVadiSatisBot',
        'token': vars.get('KEYVADI_SUPPORT_BOT_TOKEN'),
        'url': 'https://bot-service-production-9d74.up.railway.app/keyvadi/',
        'text': '🛍️ Mağazayı Aç'
    },
    {
        'name': 'LisansArenaBot',
        'token': vars.get('LISANSARENA_BOT_TOKEN') or vars.get('LISANSARENA_SUPPORT_BOT_TOKEN'),
        'url': 'https://bot-service-production-9d74.up.railway.app/la/app/',
        'text': '🛍️ Mağazayı Aç'
    },
    {
        'name': 'FroxyDestekBOT',
        'token': vars.get('FROXY_SUPPORT_BOT_TOKEN') or vars.get('FROXY_BOT_TOKEN'),
        'url': 'https://bot-service-production-9d74.up.railway.app/froxy/',
        'text': '🛍️ Mağazayı Aç'
    },
    {
        'name': 'JarvisCraftsBot',
        'token': vars.get('JARVIS_BOT_TOKEN') or vars.get('BOT_TOKEN'),
        'url': 'https://bot-service-production-9d74.up.railway.app/jarvis/app',
        'text': '⚡ Mağaza & Panel'
    }
]

for cfg in bot_configs:
    token = cfg['token']
    if not token:
        print(f"Skipping {cfg['name']} - no token")
        continue
    
    btn = {
        "type": "web_app",
        "text": cfg['text'],
        "web_app": {
            "url": cfg['url']
        }
    }
    r_mb = requests.post(
        f"https://api.telegram.org/bot{token}/setChatMenuButton",
        json={"menu_button": json.dumps(btn)}
    )
    r_get = requests.get(f"https://api.telegram.org/bot{token}/getChatMenuButton")
    print(f"{cfg['name']}:")
    print(f"  Result: {r_get.json().get('result')}")
