import subprocess
import json

api_key = "AQ.Ab8RN6LZ3LeqjiV4dkZP1FSEGP4kBGc6nIWrrlknsbZGHd3m8A"
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

payload = {
    "contents": [{"parts": [{"text": "Merhaba, nasılsın? Çok kısa 3 kelimeyle cevap ver."}]}]
}

try:
    res = subprocess.run([
        'curl.exe', '-s', '-H', 'Content-Type: application/json',
        '-d', json.dumps(payload),
        url
    ], capture_output=True, text=True, timeout=15)
    print("STDOUT:")
    print(res.stdout)
    if res.stderr:
        print("STDERR:", res.stderr)
except Exception as e:
    print("ERROR:", e)
