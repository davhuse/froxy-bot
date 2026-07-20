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

    def test_success_cooldown_is_per_account(self):
        automation.set_cooldown('example_group', 'KeyVadiOnline')
        with open(automation.COOLDOWN_FILE, encoding='utf-8') as f:
            data = json.load(f)
        self.assertIn('KeyVadiOnline', data['example_group'])
        self.assertNotIn('LisansArenaOnline', data['example_group'])

    def test_send_lock_blocks_duplicate_until_released(self):
        self.assertTrue(automation.claim_send_lock('example_group', 'KeyVadiOnline', ttl_seconds=60))
        self.assertFalse(automation.claim_send_lock('example_group', 'KeyVadiOnline', ttl_seconds=60))
        self.assertFalse(automation.claim_send_lock('example_group', 'LisansArenaOnline', ttl_seconds=60))
        automation.release_send_lock('example_group', 'KeyVadiOnline')
        self.assertTrue(automation.claim_send_lock('example_group', 'KeyVadiOnline', ttl_seconds=60))

    def test_only_requested_accounts_are_allowed(self):
        self.assertEqual(automation.ACTIVE_ACCOUNT_USERNAMES,
                         {'keyvadionline', 'lisansarenaonline'})

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


if __name__ == '__main__':
    unittest.main()
