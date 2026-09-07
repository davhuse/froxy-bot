import urllib.request
import json
import sys

api_key = "rnd_coICmwUZglrHzzHC84glOBZTgl1U"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

try:
    req = urllib.request.Request("https://api.render.com/v1/services?limit=20", headers=headers)
    with urllib.request.urlopen(req) as resp:
        services = json.loads(resp.read().decode('utf-8'))
        
    for item in services:
        svc = item.get("service", {})
        svc_id = svc.get("id")
        svc_name = svc.get("name")
        svc_url = svc.get("serviceDetails", {}).get("url")
        print(f"Service ID: {svc_id} | Name: {svc_name} | URL: {svc_url} | Suspended: {svc.get('suspended')}")
        
        # Get deploys
        d_req = urllib.request.Request(f"https://api.render.com/v1/services/{svc_id}/deploys?limit=5", headers=headers)
        with urllib.request.urlopen(d_req) as d_resp:
            deploys = json.loads(d_resp.read().decode('utf-8'))
            for d in deploys:
                dep = d.get("deploy", {})
                print(f"  Deploy ID: {dep.get('id')} | Status: {dep.get('status')} | Created: {dep.get('createdAt')} | Commit: {dep.get('commit', {}).get('message', '')[:60]}")
                
except Exception as e:
    print(f"Error: {e}")
