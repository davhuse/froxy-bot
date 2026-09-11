import urllib.request

url = "https://api.render.com/v1/services/srv-da6rbfu417fc73egreqg/deploys"
headers = {
    "Authorization": "Bearer rnd_ff6sp4PyEwlyiiziFhXZBFN5RaZB",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

req = urllib.request.Request(url, data=b"{}", headers=headers, method="POST")
try:
    with urllib.request.urlopen(req) as r:
        print("Deploy triggered!", r.read().decode('utf-8'))
except Exception as e:
    print("Error:", e)
