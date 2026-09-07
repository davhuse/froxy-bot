import os
import re

for root, dirs, files in os.walk('.'):
    if '.git' in root or 'venv' in root: continue
    for f in files:
        if f.endswith('.py') or f.endswith('.json') or f.endswith('.env'):
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as handle:
                    t = handle.read()
                    matches = re.findall(r'[0-9]{8,11}:[a-zA-Z0-9_-]{30,40}', t)
                    if matches:
                        print(f, matches)
            except Exception: pass
