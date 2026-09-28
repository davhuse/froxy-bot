import requests
import sys
sys.stdout.reconfigure(encoding='utf-8')
from check_shopier_jwts import vars

for brand, tok in [
    ('LisansArena', vars.get('SHOPIER_LISANSARENA_ACCESS_TOKEN')),
    ('KeyVadi', vars.get('SHOPIER_KEYVADI_ACCESS_TOKEN')),
    ('Froxy', vars.get('SHOPIER_FROXY_ACCESS_TOKEN')),
    ('Jarvis', vars.get('SHOPIER_JARVIS_ACCESS_TOKEN')),
]:
    headers = {'Authorization': f'Bearer {tok}', 'Accept': 'application/json'}
    r = requests.get('https://api.shopier.com/v1/orders?limit=5', headers=headers)
    print(f"=== {brand} Orders ===")
    if r.status_code == 200:
        orders = r.json()
        print(f"Count: {len(orders)}")
        for o in orders[:3]:
            items = ', '.join([item.get('title', '') for item in o.get('lineItems', [])])
            buyer = o.get('shippingInfo', {})
            name = f"{buyer.get('firstName', '')} {buyer.get('lastName', '')}".strip()
            total = o.get('totals', {}).get('total')
            print(f"  Order {o.get('id')}: status={o.get('status')} payment={o.get('paymentStatus')} total={total} TL | {name} | {items}")
    else:
        print(f"Error: {r.status_code} {r.text[:100]}")
