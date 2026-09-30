import requests
import json
import re

def check_main_server():
    url = "https://bot-service-production-9d74.up.railway.app"
    print(f"\n--- Checking Main Server: {url} ---")
    try:
        r = requests.get(url, timeout=15)
        print(f"Status Code: {r.status_code}")
        text = r.text
        
        # Check for title
        title_match = re.search(r'<title>(.*?)</title>', text)
        print(f"Title: {title_match.group(1) if title_match else 'None'}")
        
        # Check for English or Jarvis
        has_jarvis = "jarvis" in text.lower()
        has_control_center = "control center" in text.lower()
        has_keyvadi = "keyvadi" in text.lower()
        
        print(f"Contains 'KeyVadi': {has_keyvadi}")
        print(f"Contains 'Jarvis': {has_jarvis} (SHOULD BE FALSE)")
        print(f"Contains 'Control Center': {has_control_center} (SHOULD BE FALSE)")
    except Exception as e:
        print("Error checking main server:", e)

def check_dp_server():
    base_url = "https://dijital-pazarim-service-production.up.railway.app"
    print(f"\n--- Checking Dijital Pazarim Dashboard: {base_url} ---")
    try:
        r = requests.get(base_url, timeout=15)
        print(f"Dashboard Status Code: {r.status_code}")
        text = r.text
        has_dp = "dijital pazarım" in text.lower()
        has_start = "başlat" in text.lower()
        has_stop = "durdur" in text.lower()
        has_broadcast = "gruplara toplu duyuru gönder" in text.lower()
        print(f"Contains 'Dijital Pazarım': {has_dp}")
        print(f"Contains 'Başlat': {has_start}")
        print(f"Contains 'Durdur': {has_stop}")
        print(f"Contains 'Gruplara Toplu Duyuru Gönder': {has_broadcast}")
    except Exception as e:
        print("Error checking DP dashboard:", e)

    print(f"\n--- Checking Dijital Pazarim Mini App: {base_url}/dp ---")
    try:
        r = requests.get(f"{base_url}/dp", timeout=15)
        print(f"Mini App Status Code: {r.status_code}")
        text = r.text
        has_dp = "dijital pazarım" in text.lower()
        has_magaza = "mağaza" in text.lower()
        has_bakiye = "bakiye" in text.lower()
        has_siparis = "siparişlerim" in text.lower()
        has_hesabim = "hesabım" in text.lower()
        has_bottom_nav = "bottom-nav" in text.lower()
        print(f"Contains 'Dijital Pazarım': {has_dp}")
        print(f"Tab 'Mağaza': {has_magaza}")
        print(f"Tab 'Bakiye': {has_bakiye}")
        print(f"Tab 'Siparişlerim': {has_siparis}")
        print(f"Tab 'Hesabım': {has_hesabim}")
        print(f"Contains Bottom Nav Bar: {has_bottom_nav}")
    except Exception as e:
        print("Error checking DP miniapp:", e)

    print(f"\n--- Checking Dijital Pazarim API Status: {base_url}/api/status ---")
    try:
        r = requests.get(f"{base_url}/api/status", timeout=15)
        print(f"API Status Code: {r.status_code}")
        data = r.json()
        print(f"Ad Running: {data.get('ad_running')}")
        print(f"Watchdog Status: {data.get('watchdog')}")
        print(f"Target Groups Count: {data.get('target_groups_count')}")
        print(f"Joined Groups Count: {data.get('joined_groups_count')}")
        print("Full Status JSON:", json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print("Error checking DP API status:", e)

def check_keyvadi_templates():
    import glob
    print(f"\n--- Checking KeyVadi Templates for Shopier Links ---")
    files = glob.glob("messages/*keyvadi*.txt")
    shopier_found = []
    for f in files:
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            content = fp.read()
            if "shopier.com" in content:
                shopier_found.append(f)
    if shopier_found:
        print(f"WARNING: Shopier links found in: {shopier_found}")
    else:
        print(f"SUCCESS: 0 Shopier links found across all {len(files)} KeyVadi template files!")

if __name__ == "__main__":
    check_keyvadi_templates()
    check_main_server()
    check_dp_server()
