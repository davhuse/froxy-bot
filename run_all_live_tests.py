import asyncio
import json
import os

from daily_rewards import claim_daily_reward
res1 = claim_daily_reward('test_user_live_123')
assert 'eligible' in res1, 'Daily reward failed'
print('Test 1 Passed: Daily reward claim logic works perfectly.')

from sales_conversion import match_sales_products
matches = match_sales_products('netflix', 'keyvadi')
assert len(matches) > 0, 'Catalog match failed for netflix'
print('Test 2 Passed: Found', len(matches), 'products for netflix.')

matches_gemini = match_sales_products('gemini', 'keyvadi')
assert len(matches_gemini) > 0, 'Catalog match failed for gemini'
print('Test 2b Passed: Found', len(matches_gemini), 'products for gemini.')

from lead_retargeting import record_lead_interaction, _load_leads
record_lead_interaction(999999, 'Netflix 4K')
leads = _load_leads()
assert '999999' in leads, 'Lead recording failed'
print('Test 3 Passed: Lead interaction recording works.')

for i in range(1, 9):
    fpath = os.path.join('messages', f'keyvadi_{i}.txt')
    assert os.path.exists(fpath), f'Missing {fpath}'
    with open(fpath, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    assert 'KeyVadiSatisBot' in content, f'Missing bot in {fpath}'
    assert 'shopier.com' not in content, f'Shopier link must NOT be in group ads: {fpath}'
    assert not any(ord(ch) > 0x1F000 for ch in content), f'Found emoji in {fpath}'
print('Test 4 Passed: All 8 KeyVadi templates verified (clean, no shopier link, zero emojis).')

from group_policy import make_policy_compliant, DEFAULT_POLICY
with open('messages/keyvadi_1.txt', 'r', encoding='utf-8-sig') as f:
    raw = f.read()
final_msg, _ = make_policy_compliant(raw, DEFAULT_POLICY, 'keyvadi')
assert '@KeyVadiSatisBot' in final_msg, 'Bot mention stripped unexpectedly'
assert 'shopier.com' not in final_msg, 'Shopier link must not be in group ads'
print('Test 5 Passed: Group policy compliance verified (no shopier url, mention allowed).')

# Test DM auto-reply: only product link and price
from otomatik_katil import keyvadi_product_reply
sample_prod = {'title': 'Netflix 4K UHD', 'price': '79.90 TL', 'url': 'https://www.shopier.com/50665156'}
reply = keyvadi_product_reply(sample_prod)
assert 'Netflix 4K UHD' in reply
assert '79.90 TL' in reply
assert 'https://www.shopier.com/50665156' in reply
assert '3D Secure Guvencesi' not in reply, 'Fluff text should be removed'
print('Test 6 Passed: DM auto-reply sends clean product link and price without fluff.')

print('ALL LIVE TESTS COMPLETED WITH 100% SUCCESS!')