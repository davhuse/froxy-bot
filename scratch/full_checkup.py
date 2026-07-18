import urllib.request
import json
import ssl
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base_url = "https://veridia-bot.onrender.com/api"

def check_endpoint(endpoint):
    url = f"{base_url}/{endpoint}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print(f"Error checking {endpoint}: {e}")
        return None

def main():
    print("=" * 80)
    print("SYSTEM HEALTH CHECK-UP REPORT")
    print("=" * 80)
    
    # 1. Check process statuses
    ad_status = check_endpoint("status")
    froxy_status = check_endpoint("froxy/status")
    lisans_status = check_endpoint("lisansarena/status")
    
    print("\n[1] PROCESS STATUSES:")
    print(f"  * Ad Blast Bot (otomatik_katil.py): {ad_status.get('status', 'Unknown') if ad_status else 'Failed to check'}")
    print(f"  * Froxy AI Support Bot (froxy_destek_bot.py): {froxy_status.get('status', 'Unknown') if froxy_status else 'Failed to check'}")
    print(f"  * LisansArena Support Bot (lisansarena_bot.py): {lisans_status.get('status', 'Unknown') if lisans_status else 'Failed to check'}")
    
    # 2. Check Ad stats
    stats = check_endpoint("stats")
    if stats:
        print("\n[2] ADVERTISER BOT STATISTICS:")
        print(f"  * Active/Total Groups Whitelisted: {stats.get('total_groups', 0)}")
        print(f"  * Sent Messages (Current Session): {stats.get('sent_messages', 0)}")
        print(f"  * Completed Group Iterations: {stats.get('done_groups', 0)}")
        print(f"  * Blacklisted Groups (Excluding Targets): {stats.get('blacklist_groups', 0)}")
        print(f"  * Auto-Discovered Groups: {stats.get('auto_discovered', 0)}")
        
    # 3. Check Froxy logs for errors
    print("\n[3] FROXY AI SUPPORT BOT LOG HIGHLIGHTS:")
    froxy_logs = check_endpoint("froxy/logs")
    if froxy_logs and "logs" in froxy_logs:
        logs = froxy_logs["logs"]
        print(f"  Total log lines: {len(logs)}")
        error_lines = [l.strip() for l in logs if any(x in l.lower() for x in ["error", "fail", "exception", "flood", "invalid"])]
        if error_lines:
            print(f"  Found {len(error_lines)} warning/error lines in logs (last 5 shown):")
            for el in error_lines[-5:]:
                safe_el = el.encode('utf-8', errors='replace').decode('utf-8')
                print(f"    - {safe_el}")
        else:
            print("  No warnings or errors found in logs.")
            
    # 4. Check LisansArena logs for errors
    print("\n[4] LISANSARENA SUPPORT BOT LOG HIGHLIGHTS:")
    lisans_logs = check_endpoint("lisansarena/logs")
    if lisans_logs and "logs" in lisans_logs:
        logs = lisans_logs["logs"]
        print(f"  Total log lines: {len(logs)}")
        error_lines = [l.strip() for l in logs if any(x in l.lower() for x in ["error", "fail", "exception", "flood", "invalid"])]
        if error_lines:
            print(f"  Found {len(error_lines)} warning/error lines in logs (last 5 shown):")
            for el in error_lines[-5:]:
                safe_el = el.encode('utf-8', errors='replace').decode('utf-8')
                print(f"    - {safe_el}")
        else:
            print("  No warnings or errors found in logs.")
            
    # 5. Check Ad logs (last 15 lines)
    print("\n[5] AD BLAST BOT LATEST LOGS:")
    ad_logs = check_endpoint("logs")
    if ad_logs and "logs" in ad_logs:
        logs = ad_logs["logs"]
        for line in logs[-15:]:
            safe_line = line.strip().encode('utf-8', errors='replace').decode('utf-8')
            print(f"  {safe_line}")
            
    print("\n" + "=" * 80)
    print("CHECK-UP COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
