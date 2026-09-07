import urllib.request
import json
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

base_url = 'https://froxy-bot-kgky.onrender.com'

# 1. Check Froxy models
req_models = urllib.request.Request(f'{base_url}/froxy/api/models')
with urllib.request.urlopen(req_models) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print('=== FROXY MODELS ===')
    print('Model count:', len(data.get('models', [])))
    for m in data.get('models', []):
        print(f" - {m.get('name')} [{m.get('provider_label')}] -> {m.get('provider_logo')}")

# 2. Check Froxy image models
req_img = urllib.request.Request(f'{base_url}/froxy/api/image-models')
with urllib.request.urlopen(req_img) as resp:
    data_img = json.loads(resp.read().decode('utf-8'))
    print('\n=== FROXY IMAGE MODELS ===')
    print('Image models count:', len(data_img.get('models', [])))
    for im in data_img.get('models', []):
        print(f" - {im.get('name')} [{im.get('provider_label')}] -> Active: {im.get('active')} -> {im.get('provider_logo')}")
