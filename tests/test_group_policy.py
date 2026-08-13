import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import group_policy


class GroupPolicyTests(unittest.TestCase):
    def test_numeric_id_has_priority_over_username(self):
        entity = SimpleNamespace(id=3065608337, username="renamed_group", default_banned_rights=None)
        key, policy = group_policy.resolve_group_policy("unrelated", entity)
        self.assertEqual(key, "id:3065608337")
        self.assertFalse(policy["allow_urls"])

    def test_link_forbidden_keyvadi_copy_has_no_url_entity_or_mention(self):
        entity = SimpleNamespace(id=3065608337, username="ceksatkupon2", default_banned_rights=None)
        _, policy = group_policy.resolve_group_policy("ceksatkupon2", entity)
        message = (
            "KeyVadi ürün listesi\nCanva Pro 49,90 TL\n"
            "[@KeyVadiSatisBot](https://t.me/KeyVadiSatisBot?start=cta_k_t_1234567890)"
        )
        text, options = group_policy.make_policy_compliant(message, policy, "keyvadi")
        self.assertIn("Canva Pro 49,90 TL", text)
        self.assertTrue(text.endswith(group_policy.PLAIN_KEYVADI_CTA))
        for forbidden in ("http://", "https://", "t.me", "?start=", "@", "]("):
            self.assertNotIn(forbidden, text)
        self.assertIsNone(options["parse_mode"])
        self.assertFalse(options["link_preview"])
        self.assertFalse(options["allow_media"])

    def test_telegram_embed_link_ban_overrides_default_policy(self):
        rights = SimpleNamespace(embed_links=True, send_media=False)
        policy = group_policy.apply_telegram_rights(group_policy.DEFAULT_POLICY, SimpleNamespace(default_banned_rights=rights))
        self.assertFalse(policy["allow_urls"])
        self.assertFalse(policy["allow_deep_links"])

    def test_cas_seed_holds_only_keyvadi(self):
        entity = SimpleNamespace(id=2780340773, username="ceksatkupon", default_banned_rights=None)
        _, policy = group_policy.resolve_group_policy("ceksatkupon", entity)
        self.assertTrue(group_policy.account_is_held(policy, "keyvadi"))
        self.assertFalse(group_policy.account_is_held(policy, "froxy"))

    def test_second_link_protected_group_waits_for_controlled_smoke(self):
        entity = SimpleNamespace(id=1511926667, username="kuponcekkodsatis", default_banned_rights=None)
        _, policy = group_policy.resolve_group_policy("kuponcekkodsatis", entity)
        self.assertTrue(group_policy.account_is_held(policy, "keyvadi"))

    def test_message_empty_hold_expires_after_24_hours(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "moderation.json")
            with patch.object(group_policy, "MODERATION_FILE", path):
                group_policy.record_moderation_hold("example", "KeyVadiOnline", "MessageEmpty")
                self.assertTrue(group_policy.moderation_hold_active("example", "KeyVadiOnline"))

    def test_security_warning_requires_brand_reference(self):
        text = "KeyVadiOnline mesajı izin verilmeyen link nedeniyle mesaj silindi"
        self.assertTrue(group_policy.is_moderation_warning(text))
        self.assertTrue(group_policy.warning_targets_brand(text, "keyvadi"))
        self.assertFalse(group_policy.warning_targets_brand(text, "froxy"))


if __name__ == "__main__":
    unittest.main()
