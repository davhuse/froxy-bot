import urllib.request
import json
url = "https://froxy-bot-kgky.onrender.com/api/logs"
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as r:
        pass
except:
    pass
