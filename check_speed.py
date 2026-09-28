import requests
import json
import time

r = requests.get('https://bot-service-production-9d74.up.railway.app/api/status')
kv = r.json().get('ad_accounts', {}).get('KeyVadiOnline', {})
q = r.json().get('blast_queue', {}).get('accounts', {}).get('KeyVadiOnline', {})
print(f"KeyVadi: sent={kv.get('sent_count')} failed={kv.get('failed_count')} current_idx={kv.get('current_index')}/{kv.get('total_groups')} queue_status={q.get('status')}")
