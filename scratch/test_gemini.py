import urllib.request
import ssl
import json

# Force TLS 1.2 to bypass the Windows Python TLS 1.3 Session Ticket bug
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.load_default_certs()
# Disable TLS 1.3 specifically to prevent the bug
context.options |= ssl.OP_NO_TLSv1_3

url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=AQ.Ab8RN6LZ3LeqjiV4dkZP1FSEGP4kBGc6nIWrrlknsbZGHd3m8A"
payload = {
    "contents": [
        {
            "parts": [
                {"text": "Explain AI in three words"}
            ]
        }
    ]
}

req = urllib.request.Request(
    url, 
    data=json.dumps(payload).encode('utf-8'), 
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req, context=context) as response:
        print(response.read().decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
