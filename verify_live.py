import urllib.request
import json
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

base_url = 'https://froxy-bot-kgky.onrender.com'

# 1. System status
req = urllib.request.Request(f'{base_url}/api/status')
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print('=== LIVE STATUS ===')
    print('Build:', data.get('build'))
    print('Bot Runtime Enabled:', data.get('bot_runtime_enabled'))
    print('Froxy Support Processes:', data.get('froxy_support_processes'))
    print('KeyVadi Support Processes:', data.get('support_processes'))
    print('LisansArena Processes:', data.get('lisansarena_processes'))
    print('Ad Runtime Enabled:', data.get('ad_runtime_enabled'))

# 2. Mini App Products
req2 = urllib.request.Request(f'{base_url}/froxy/api/products')
with urllib.request.urlopen(req2) as resp:
    data2 = json.loads(resp.read().decode('utf-8'))
    print('\n=== LIVE FROXY PRODUCTS ===')
    print('Total products:', len(data2.get('products', [])))
    for p in data2.get('products', [])[:6]:
        print(f" - {p.get('title')} [{p.get('price')}] -> Img: {p.get('image')}")
