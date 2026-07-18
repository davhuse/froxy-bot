import urllib.request
import json
import ssl
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://veridia-bot.onrender.com/api/full_logs"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

try:
    with urllib.request.urlopen(req, context=ctx) as r:
        logs = r.read().decode("utf-8").split("\n")
        print(f"Total log lines: {len(logs)}")
        
        # Search for errors or warnings related to bans, kicks, or write restrictions
        search_terms = ["ban", "kick", "restrict", "forbidden", "write", "rose", "block", "error", "fail"]
        matching_lines = []
        
        for line in logs:
            lower_line = line.lower()
            if any(term in lower_line for term in search_terms):
                matching_lines.append(line.strip())
                
        print(f"\nFound {len(matching_lines)} potential restriction/ban/error logs:")
        for ml in matching_lines[-50:]: # Show last 50 matches
            safe_ml = ml.encode('utf-8', errors='replace').decode('utf-8')
            print(f"  {safe_ml}")
            
except Exception as e:
    print("Error:", e)
