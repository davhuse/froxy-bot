import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {
    'Content-Type': 'application/json',
}
api_key = "AQ.Ab8RN6LZ3LeqjiV4dkZP1FSEGP4kBGc6nIWrrlknsbZGHd3m8A"
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
data = {
    "contents": [{"parts": [{"text": "Merhaba, nasılsın?"}]}]
}

# Python on Windows has a known TLS 1.3 Session Ticket bug that throws "INVALID_SESSION_ID".
# We set Connection: close to prevent session reuse and bypass this bug.
try:
    r = requests.post(url, json=data, headers={'Connection': 'close'}, verify=True, timeout=10)
    print("STATUS:", r.status_code)
    print("RESPONSE:", r.text)
except Exception as e:
    print("ERROR:", e)
