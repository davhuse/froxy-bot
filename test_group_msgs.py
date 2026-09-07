import group_policy
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

key_policy_key, policy = group_policy.resolve_group_policy("kodkuponcek")

with open("messages/froxy_hook.txt", "r", encoding="utf-8") as f:
    froxy_raw = f.read()
froxy_text, _ = group_policy.make_policy_compliant(froxy_raw, policy, "froxy")

with open("messages/keyvadi_1.txt", "r", encoding="utf-8") as f:
    keyvadi_raw = f.read()
keyvadi_text, _ = group_policy.make_policy_compliant(keyvadi_raw, policy, "keyvadi")

with open("output_group_msgs.txt", "w", encoding="utf-8") as f:
    f.write("=== FROXY ===\n")
    f.write(froxy_text)
    f.write(f"\nSatır Sayısı: {len(froxy_text.splitlines())}\n\n")
    f.write("=== KEYVADI ===\n")
    f.write(keyvadi_text)
    f.write(f"\nSatır Sayısı: {len(keyvadi_text.splitlines())}\n")

print("Generated!")
