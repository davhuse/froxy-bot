import requests
from check_shopier_jwts import vars

for name, token in [
    ('LISANSARENA', vars.get('SHOPIER_LISANSARENA_ACCESS_TOKEN')),
    ('KEYVADI', vars.get('SHOPIER_KEYVADI_ACCESS_TOKEN')),
    ('FROXY', vars.get('SHOPIER_FROXY_ACCESS_TOKEN')),
    ('JARVIS', vars.get('SHOPIER_JARVIS_ACCESS_TOKEN')),
]:
    print(f"\nTesting {name} token:")
    h = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    # test GET /shop or GET /products
    for endpoint in ['/shop', '/products?limit=5', '/orders?limit=5']:
        r = requests.get(f'https://api.shopier.com/v1{endpoint}', headers=h)
        print(f"  GET {endpoint} -> {r.status_code}")
        if r.status_code == 200:
            print("   ", str(r.json())[:150])
        else:
            print("   ", r.text[:150])
