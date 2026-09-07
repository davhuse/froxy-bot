import urllib.request

url = "https://api.render.com/v1/services/srv-daem9k1t0dsc73ar02dg/deploys"
headers = {
    "Authorization": "Bearer rnd_coICmwUZglrHzzHC84glOBZTgl1U",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

req = urllib.request.Request(url, data=b"{}", headers=headers, method="POST")
try:
    with urllib.request.urlopen(req) as r:
        print("Deploy triggered!", r.read().decode('utf-8'))
except Exception as e:
    print("Error:", e)
