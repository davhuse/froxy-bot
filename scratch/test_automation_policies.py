import json
import os
import tempfile
import unittest
from types import SimpleNamespace

import otomatik_katil as automation


class AutomationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original = {
            'account': automation.ACCOUNT_RESTRICTIONS_FILE,
            'failures': automation.GROUP_FAILURES_FILE,
            'cooldown': automation.COOLDOWN_FILE,
            'locks': automation.SEND_LOCK_FILE,
        }
        automation.ACCOUNT_RESTRICTIONS_FILE = os.path.join(self.tmp.name, 'account.json')
        automation.GROUP_FAILURES_FILE = os.path.join(self.tmp.name, 'failures.json')
        automation.COOLDOWN_FILE = os.path.join(self.tmp.name, 'cooldown.json')
        automation.SEND_LOCK_FILE = os.path.join(self.tmp.name, 'send_locks.json')

    def tearDown(self):
        automation.ACCOUNT_RESTRICTIONS_FILE = self.original['account']
        automation.GROUP_FAILURES_FILE = self.original['failures']
        automation.COOLDOWN_FILE = self.original['cooldown']
        automation.SEND_LOCK_FILE = self.original['locks']
        self.tmp.cleanup()

    def test_account_restriction_is_not_group_blacklist(self):
        automation.set_account_restriction('KeyVadiOnline', 3600, 'FloodWait')
        self.assertTrue(automation.is_account_restricted('KeyVadiOnline'))
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, 'blacklist.txt')))

    def test_discovery_restriction_does_not_stop_sending(self):
        automation.set_account_restriction('KeyVadiOnline', 3600, 'Telegram discovery FloodWait', 'FloodWaitError', scope='discover')
        self.assertTrue(automation.is_account_restricted('KeyVadiOnline', scope='discover'))
        self.assertFalse(automation.is_account_restricted('KeyVadiOnline', scope='send'))

    def test_join_restriction_does_not_stop_sending(self):
        automation.set_account_restriction('LisansArenaOnline', 3600, 'Telegram join FloodWait', 'FloodWaitError', scope='join')
        self.assertTrue(automation.is_account_restricted('LisansArenaOnline', scope='join'))
        self.assertFalse(automation.is_account_restricted('LisansArenaOnline', scope='send'))

    def test_temporary_group_failure_is_not_blacklist(self):
        automation.record_group_failure('example_group', 'LisansArenaOnline', 'Timeout', 300)
        self.assertTrue(automation.is_group_retry_blocked('example_group', 'LisansArenaOnline'))
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, 'blacklist.txt')))

    def test_terminal_group_failure_blocks_only_affected_account(self):
        automation.record_group_failure(
            'example_group', 'FroxyOnline', 'UserBannedInChannel', 30 * 24 * 60 * 60
        )
        self.assertTrue(automation.is_group_retry_blocked('example_group', 'FroxyOnline'))
        self.assertFalse(automation.is_group_retry_blocked('example_group', 'KeyVadiOnline'))

    def test_marketing_features_do_not_append_repetitive_deal_catalog(self):
        message = 'Canva Pro 1 Yıl: 83.99 TL\nSipariş: @KeyVadiSatisBot'
        result = automation.process_marketing_features(message, True, False)
        self.assertEqual(result, message)
        self.assertNotIn('GÜNÜN DEV FIRSATLARI', result)

    def test_dm_intent_filters_skip_non_sales_text(self):
        self.assertTrue(automation.is_obviously_non_sales_dm('selam'))
        self.assertTrue(automation.is_obviously_non_sales_dm('Allah razı olsun amin'))
        self.assertFalse(automation.is_obviously_non_sales_dm('canva pro var mı'))
        self.assertTrue(automation.has_sales_intent('canva pro var mı'))
        self.assertTrue(automation.has_explicit_sales_intent('canva pro fiyat link'))
        self.assertFalse(automation.has_explicit_sales_intent('canva pro'))

    def test_success_cooldown_is_per_account(self):
        automation.set_cooldown('example_group', 'KeyVadiOnline')
        with open(automation.COOLDOWN_FILE, encoding='utf-8') as f:
            data = json.load(f)
        self.assertIn('KeyVadiOnline', data['example_group'])
        self.assertNotIn('LisansArenaOnline', data['example_group'])
        self.assertTrue(automation.is_on_cooldown('example_group', 'KeyVadiOnline'))
        self.assertFalse(automation.is_on_cooldown('example_group', 'LisansArenaOnline'))
        automation.set_cooldown('example_group', 'LisansArenaOnline')
        self.assertTrue(automation.is_on_cooldown('example_group', 'LisansArenaOnline'))

    def test_known_group_alias_shares_cooldown(self):
        automation.set_cooldown('-1003336542169', 'KeyVadiOnline')
        self.assertTrue(automation.is_on_cooldown('Nightsatis', 'KeyVadiOnline'))
        self.assertFalse(automation.is_on_cooldown('Nightsatis', 'LisansArenaOnline'))

    def test_target_dedupe_prefers_chat_id(self):
        entity = SimpleNamespace(id=12345, username='example_group')
        self.assertEqual(automation.target_dedupe_key('example_group', entity), '12345')
        self.assertEqual(automation.target_dedupe_key('-10012345', entity), '12345')
        self.assertNotEqual(
            automation.target_dedupe_key('example_group', entity),
            automation.target_dedupe_key('example_group', None),
        )

    def test_reference_channels_are_excluded_by_username_or_chat_id(self):
        self.assertTrue(automation.is_reference_channel('@FroxyReferans'))
        self.assertTrue(automation.is_reference_channel('-1004316589940'))
        entity = SimpleNamespace(id=4401324614, username=None)
        self.assertTrue(automation.is_reference_channel('some_numeric_alias', entity))
        self.assertFalse(automation.is_reference_channel('ticaretforumofficial'))

    def test_manually_removed_groups_stay_out_of_joined_group_blasts(self):
        for group in (
            'illegalalimsatimerkezi', 'sultanbeyliikinciel0',
            'ReklamOnliene', 'ReferansReklamYardimlasma',
        ):
            entity = SimpleNamespace(id=123, username=group)
            self.assertTrue(automation.is_excluded_ad_target(group, entity), group)
            self.assertFalse(automation.is_group_protected(group), group)
        self.assertTrue(automation.is_group_protected('zeroticaret'))

    def test_send_lock_blocks_duplicate_until_released(self):
        self.assertTrue(automation.claim_send_lock('example_group', 'KeyVadiOnline', ttl_seconds=60))
        self.assertFalse(automation.claim_send_lock('example_group', 'KeyVadiOnline', ttl_seconds=60))
        self.assertFalse(automation.claim_send_lock('example_group', 'LisansArenaOnline', ttl_seconds=60))
        automation.release_send_lock('example_group', 'KeyVadiOnline')
        self.assertTrue(automation.claim_send_lock('example_group', 'KeyVadiOnline', ttl_seconds=60))

    def test_only_requested_accounts_are_allowed(self):
        self.assertEqual(automation.ACTIVE_ACCOUNT_USERNAMES,
                         {'keyvadionline', 'lisansarenaonline', 'froxy_ai'})
        self.assertEqual(automation.account_brand('FroxyOnline'), 'froxy')
        self.assertEqual(automation.account_brand('LisansArenaOnline'), 'lisansarena')
        self.assertEqual(automation.account_brand('KeyVadiOnline'), 'keyvadi')

    def test_manually_approved_groups_are_protected_targets(self):
        for group in (
            'TicaretGrubuuu', 'kuponceking', 'ticaretsaha',
            'Nightsatis', 'kuponsatimalim', 'kuponindirimsatis',
        ):
            self.assertTrue(automation.is_group_protected(group), group)

    def test_protected_group_alias_blocks_numeric_blacklist(self):
        self.assertTrue(automation.is_group_protected('Nightsatis'))
        self.assertTrue(automation.is_group_protected('-1003336542169'))

    def test_ticaret_forum_detected_by_username_or_title(self):
        self.assertTrue(automation.is_ticaret_forum_group('ticaretforumofficial'))
        entity = SimpleNamespace(username=None, title='Hashtag Ticaret Forum Official')
        self.assertTrue(automation.is_ticaret_forum_group('123456', entity))

    def test_ticaret_forum_message_is_short_and_has_single_bot_route(self):
        message = automation.ticaret_forum_message(True, False)
        self.assertLessEqual(len(message), automation.TICARET_FORUM_MAX_CHARS)
        self.assertIn('@KeyVadiSatisBot', message)
        self.assertEqual(
            automation.process_marketing_features(message, True, False, is_short=True),
            message.strip(),
        )
        froxy_message = automation.ticaret_forum_message(False, False, True)
        self.assertLessEqual(len(froxy_message), automation.TICARET_FORUM_MAX_CHARS)
        self.assertIn('@FroxyDestekBOT', froxy_message)


if __name__ == '__main__':
    unittest.main()
