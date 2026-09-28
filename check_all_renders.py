import urllib.request
import json
import ssl
import sys

sys.stdout.reconfigure(encoding='utf-8')

keys = [
    ('rnd_4c83vU85zEZ7KOjaS5crYqM4x55G', 'Account 1 (4c83)'),
    ('rnd_coICmwUZglrHzzHC84glOBZTgl1U', 'Account 2 (coIC)'),
    ('rnd_ff6sp4PyEwlyiiziFhXZBFN5RaZB', 'Account 3 (ff6s)'),
    ('rnd_ZZBuiyIs7CovoIdsbe2vYRE2IXs4', 'Account 4 (ZZBu)'),
    ('rnd_uSYeDJkX0xrcNfgo2BP7Tu3dRvuE', 'Account 5 (uSYe)')
]

ctx = ssl._create_unverified_context()

for k, label in keys:
    print(f"=== {label} : {k[:10]}... ===")
    req = urllib.request.Request("https://api.render.com/v1/services?limit=20")
    req.add_header("Authorization", f"Bearer {k}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            services = json.loads(r.read().decode('utf-8'))
            for s in services:
                svc = s.get("service", s)
                print(f"  ID: {svc.get('id')} | Name: {svc.get('name')} | Slug: {svc.get('slug')} | Suspended: {svc.get('suspended')}")
    except Exception as e:
        print(f"  Error: {e}")
