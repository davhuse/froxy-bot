import urllib.request
import json

services = [
    ('rnd_4c83vU85zEZ7KOjaS5crYqM4x55G', 'srv-danfkkek1f9s738iq5rg', 'froxy-bot-1 (CURRENT)'),
    ('rnd_4c83vU85zEZ7KOjaS5crYqM4x55G', 'srv-d9ln2c2jobas73bhe7ag', 'froxy-bot (4c83)'),
    ('rnd_coICmwUZglrHzzHC84glOBZTgl1U', 'srv-daem9k1t0dsc73ar02dg', 'froxy-bot (coIC)'),
    ('rnd_ff6sp4PyEwlyiiziFhXZBFN5RaZB', 'srv-da6rbfu417fc73egreqg', 'froxy-bot-live (ff6s)'),
    ('rnd_ZZBuiyIs7CovoIdsbe2vYRE2IXs4', 'srv-dakqrl1594qs7398ia6g', 'froxy-bot-live (ZZBu)'),
]

all_env = {}

for key, srv_id, label in services:
    req = urllib.request.Request(f'https://api.render.com/v1/services/{srv_id}/env-vars', headers={'Authorization': f'Bearer {key}'})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            all_env[label] = {item['envVar']['key']: item['envVar']['value'] for item in data}
            print(f"Loaded {len(all_env[label])} env vars from {label}")
    except Exception as e:
        print(f"Failed {label}: {e}")

with open('extracted_all_render_envs.json', 'w', encoding='utf-8') as f:
    json.dump(all_env, f, indent=2, ensure_ascii=False)

print("Saved to extracted_all_render_envs.json")
