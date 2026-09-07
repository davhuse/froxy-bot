import group_policy
import sys

sys.stdout.reconfigure(encoding="utf-8")

# Let's test strict_group_safe_copy for KeyVadi and Froxy
from otomatik_katil import strict_group_safe_copy, sanitize_strict_market_message

key_policy_key, policy = group_policy.resolve_group_policy("kodkuponcek")

print("=== KEYVADI (kupongrupta stili) ===")
raw_kv = sanitize_strict_market_message("orijinal", "kupongrupta", True, False, False)
final_kv, _ = group_policy.make_policy_compliant(raw_kv, policy, "keyvadi")
print(final_kv)
print(f"Satır Sayısı: {len(final_kv.splitlines())}")

print("\n=== FROXY (kupongrupta stili) ===")
raw_fx = sanitize_strict_market_message("orijinal", "kupongrupta", False, False, True)
final_fx, _ = group_policy.make_policy_compliant(raw_fx, policy, "froxy")
print(final_fx)
print(f"Satır Sayısı: {len(final_fx.splitlines())}")
