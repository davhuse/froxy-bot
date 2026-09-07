import re

with open("otomatik_katil.py", "r", encoding="utf-8") as f:
    content = f.read()

old_code = """    active_account_names = {name for _, name, _ in active_clients}"""
new_code = """    disabled_accounts_for_queue = disabled_ad_accounts()
    active_account_names = {name for _, name, _ in active_clients if name.casefold() not in disabled_accounts_for_queue}"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open("otomatik_katil.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched!")
else:
    print("Not found.")
