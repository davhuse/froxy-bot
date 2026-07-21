import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        # Set options to disable TLS 1.3 session tickets or configure TLS 1.2
        context.options |= 0x4000  # SSL_OP_NO_TICKET
        # Force TLS 1.2 to completely bypass TLS 1.3 session ticket bugs on Windows Python
        context.check_hostname = False
        context.verify_mode = 0  # Ignore verification for test purposes
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

api_key = "AQ.Ab8RN6LZ3LeqjiV4dkZP1FSEGP4kBGc6nIWrrlknsbZGHd3m8A"
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
data = {
    "contents": [{"parts": [{"text": "Hello"}]}]
}

session = requests.Session()
session.mount('https://', TLSAdapter())

try:
    r = session.post(url, json=data, timeout=10, verify=False)
    print("STATUS:", r.status_code)
    print("RESPONSE:", r.text)
except Exception as e:
    print("ERROR:", e)
