import urllib.request
import json

keys = [
    'rnd_4c83vU85zEZ7KOjaS5crYqM4x55G',
    'rnd_coICmwUZglrHzzHC84glOBZTgl1U',
    'rnd_ff6sp4PyEwlyiiziFhXZBFN5RaZB',
    'rnd_ZZBuiyIs7CovoIdsbe2vYRE2IXs4',
    'rnd_uSYeDJkX0xrcNfgo2BP7Tu3dRvuE'
]

for k in keys:
    req = urllib.request.Request('https://api.render.com/v1/services', headers={'Authorization': f'Bearer {k}'})
    try:
        with urllib.request.urlopen(req) as resp:
            services = json.loads(resp.read().decode())
            print(f'=== KEY {k[:10]}... SUCCESS ({len(services)} services) ===')
            for s in services:
                srv = s.get('service', {})
                print(f"  Service: {srv.get('name')} | id: {srv.get('id')} | suspended: {srv.get('suspended')}")
    except Exception as e:
        print(f'Key {k[:10]}... failed: {e}')
