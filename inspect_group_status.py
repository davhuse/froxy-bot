import urllib.request
import json
import ssl
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
token = 'VOJVbVkVHQBw5J3zI8vQeW2zP5iK6uY9'
req = urllib.request.Request(
    'https://froxy-bot-kgky.onrender.com/api/group-status',
    headers={'X-Admin-Token': token}
)
with urllib.request.urlopen(req, context=ctx) as r:
    data = json.loads(r.read().decode('utf-8'))

print("=== PERMANENT BLOCKS (Total: %d) ===" % len(data.get('permanent', [])))
for item in data.get('permanent', []):
    print("  %s: @%s -> %s" % (item.get('account'), item.get('group'), item.get('reason')))

print("\n=== REVIEW / QUARANTINE BLOCKS (Total: %d) ===" % len(data.get('review', [])))
for item in data.get('review', []):
    print("  %s: @%s -> %s (Retry: %s)" % (item.get('account'), item.get('group'), item.get('reason'), item.get('retry_at')))
