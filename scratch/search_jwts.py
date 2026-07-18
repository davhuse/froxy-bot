import os
import re

dir_path = r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam"

found = []
for root, dirs, files in os.walk(dir_path):
    for f in files:
        if f.endswith((".py", ".json", ".txt", ".html")):
            fp = os.path.join(root, f)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as file:
                    content = file.read()
                    matches = re.findall(r'eyJ0eXAi[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+', content)
                    for m in matches:
                        found.append((f, m))
            except Exception as e:
                pass

print(f"Found {len(found)} JWT tokens:")
for fname, tok in found:
    # Decode token payload to see the audience/subject
    import base64
    try:
        parts = tok.split('.')
        payload_b64 = parts[1]
        # Pad payload
        payload_b64 += '=' * (-len(payload_b64) % 4)
        payload = base64.b64decode(payload_b64).decode('utf-8')
        print(f"File: {fname}")
        print(f"Payload: {payload}")
        print("-" * 50)
    except Exception as e:
        print(f"File: {fname} (Failed to decode: {e})")
