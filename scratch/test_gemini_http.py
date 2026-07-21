import http.client
import json
import ssl

api_key = "AQ.Ab8RN6LZ3LeqjiV4dkZP1FSEGP4kBGc6nIWrrlknsbZGHd3m8A"
path = f"/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
host = "generativelanguage.googleapis.com"

# Disable SSL/TLS session ticket to prevent session reuse (fixes the Windows invalid session id bug)
context = ssl.create_default_context()
context.options |= ssl.OP_NO_TICKET

payload = {
    "contents": [{"parts": [{"text": "Explain AI in three words"}]}]
}

conn = http.client.HTTPSConnection(host, context=context)
headers = {"Content-Type": "application/json"}

try:
    conn.request("POST", path, body=json.dumps(payload), headers=headers)
    res = conn.getresponse()
    print("STATUS:", res.status)
    print("BODY:", res.read().decode('utf-8'))
except Exception as e:
    print("ERROR:", e)
finally:
    conn.close()
