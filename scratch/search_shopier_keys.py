import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("Searching codebase for Shopier API credentials/keys...")

found = False
for root, dirs, files in os.walk('.'):
    # Skip virtual environments or system directories
    if any(k in root for k in ['venv', '.git', '__pycache__', 'scratch']):
        continue
    for file in files:
        if file.endswith('.py') or file.endswith('.json') or file.endswith('.txt'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                # Check for shopier api credentials patterns
                if 'shopier' in content.lower():
                    matches = re.findall(r'([a-zA-Z0-9_\-]*api[a-zA-Z0-9_\-]*\s*=\s*[\'"][^\'"]+[\'"])', content, re.I)
                    matches_key = re.findall(r'([a-zA-Z0-9_\-]*key[a-zA-Z0-9_\-]*\s*=\s*[\'"][^\'"]+[\'"])', content, re.I)
                    all_m = list(set(matches + matches_key))
                    if all_m:
                        print(f"\nFile: {path}")
                        for m in all_m:
                            print(f"  Found: {m.strip()}")
                        found = True
            except Exception as e:
                pass

if not found:
    print("No direct Shopier API credentials found in code files.")
