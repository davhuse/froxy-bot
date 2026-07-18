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
        print(f"Total log lines retrieved: {len(logs)}")
        
        # Filter lines containing join, katil, error, black, target
        join_lines = []
        for line in logs:
            lower_line = line.lower()
            if any(x in lower_line for x in ["katıl", "join", "istek", "request", "invitation", "hedef", "limit", "flood"]):
                join_lines.append(line.strip())
                
        print(f"\nFound {len(join_lines)} join/target related log lines:")
        for jl in join_lines[-50:]: # Show last 50 lines
            safe_jl = jl.encode('utf-8', errors='replace').decode('utf-8')
            print(f"  {safe_jl}")
            
except Exception as e:
    print("Error:", e)
