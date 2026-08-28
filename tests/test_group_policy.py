import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import group_policy


class GroupPolicyTests(unittest.TestCase):
    def test_moderation_hold_progresses_from_one_to_six_to_twenty_four_hours(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "moderation.json")
            with patch.object(group_policy, "MODERATION_FILE", path):
                durations = []
                for _ in range(3):
                    group_policy.record_moderation_hold("warned", "FroxyOnline", "deleted")
                    states = group_policy._load(path)
                    state = next(iter(states.values()))["FroxyOnline"]
                    from datetime import datetime, timezone
                    hold = datetime.fromisoformat(state["hold_until"])
                    updated = datetime.fromisoformat(state["updated_at"])
                    durations.append(round((hold - updated).total_seconds() / 3600))
                self.assertEqual(durations, [1, 6, 24])

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

    def test_default_group_uses_visible_keyvadi_mention_without_link(self):
        policy = group_policy.apply_brand_link_safety(group_policy.DEFAULT_POLICY, "keyvadi")
        message = (
            "Canva Pro 49,90 TL\n"
            "Sipariş Adresi: [@KeyVadiSatisBot]"
            "(https://t.me/KeyVadiSatisBot?start=cta_k_t_1234567890)"
        )
        text, options = group_policy.make_policy_compliant(message, policy, "keyvadi")
        self.assertIn("Canva Pro 49,90 TL", text)
        self.assertIn("@KeyVadiSatisBot", text)
        self.assertNotIn("https://", text)
        self.assertNotIn("t.me", text)
        self.assertNotIn("?start=", text)
        self.assertEqual(options["parse_mode"], None)
        self.assertEqual(options["cta_mode"], "plain_mention")
        self.assertFalse(options["link_preview"])

    def test_persistent_moderation_warning_keeps_group_on_search_cta(self):
        policy = dict(group_policy.DEFAULT_POLICY)
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "moderation.json")
            with patch.object(group_policy, "MODERATION_FILE", path):
                group_policy.record_moderation_hold(
                    "warned", "FroxyOnline", "izin verilmeyen link", hours=0
                )
                safe_policy = group_policy.apply_persistent_moderation_safety(
                    policy, "warned"
                )
                text, options = group_policy.make_policy_compliant(
                    "Ürün listesi\n@FroxyDestekBOT", safe_policy, "froxy"
                )
        self.assertNotIn("@", text)
        self.assertTrue(text.endswith(group_policy.PLAIN_FROXY_CTA))
        self.assertEqual(options["cta_mode"], "policy_plain_text")

    def test_darcy_spam_warning_is_detected(self):
        warning = "@KeyVadiDestek grup veya kanal spamı gönderdi. Eylem: Sessize aldım"
        self.assertTrue(group_policy.is_moderation_warning(warning))
        self.assertTrue(group_policy.warning_targets_brand(warning, "keyvadi"))

    def test_cas_seed_holds_only_keyvadi(self):
        entity = SimpleNamespace(id=2780340773, username="ceksatkupon", default_banned_rights=None)
        _, policy = group_policy.resolve_group_policy("ceksatkupon", entity)
        self.assertTrue(group_policy.account_is_held(policy, "keyvadi"))
        self.assertFalse(group_policy.account_is_held(policy, "froxy"))

    def test_second_link_protected_group_waits_for_controlled_smoke(self):
        entity = SimpleNamespace(id=1511926667, username="kuponcekkodsatis", default_banned_rights=None)
        _, policy = group_policy.resolve_group_policy("kuponcekkodsatis", entity)
        self.assertFalse(group_policy.account_is_held(policy, "keyvadi"))
        self.assertTrue(policy["smoke_required"])

    def test_indirim363_security_bot_hold_covers_both_muted_accounts(self):
        entity = SimpleNamespace(id=2846540634, username="indirim363", default_banned_rights=None)
        _, policy = group_policy.resolve_group_policy("indirim363", entity)
        self.assertFalse(group_policy.account_is_held(policy, "keyvadi"))
        self.assertFalse(group_policy.account_is_held(policy, "froxy"))
        self.assertTrue(policy["smoke_required"])
        self.assertFalse(policy["allow_urls"])

    def test_smoke_is_serialized_across_accounts_and_passes_at_ten_minutes(self):
        entity = SimpleNamespace(id=2846540634, username="indirim363", default_banned_rights=None)
        _, policy = group_policy.resolve_group_policy("indirim363", entity)
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "moderation.json")
            with patch.object(group_policy, "MODERATION_FILE", path):
                self.assertTrue(group_policy.policy_smoke_pending(
                    "indirim363", "FroxyOnline", policy, entity=entity
                ))
                group_policy.record_delivery_state(
                    "indirim363", "FroxyOnline", "policy_smoke_sent", entity=entity
                )
                self.assertTrue(group_policy.visibility_check_pending(
                    "indirim363", entity=entity
                ))
                self.assertFalse(group_policy.policy_smoke_available(
                    "indirim363", "KeyVadiOnline", entity=entity
                ))
                group_policy.record_delivery_state(
                    "indirim363", "FroxyOnline", "visible_10m", entity=entity
                )
                self.assertFalse(group_policy.policy_smoke_pending(
                    "indirim363", "FroxyOnline", policy, entity=entity
                ))
                self.assertFalse(group_policy.visibility_check_pending(
                    "indirim363", entity=entity
                ))

    def test_link_forbidden_froxy_copy_has_plain_cta_and_max_lines(self):
        policy = {**group_policy.DEFAULT_POLICY, "allow_urls": False,
                  "allow_deep_links": False, "allow_mentions": False,
                  "max_lines": 3}
        text, options = group_policy.make_policy_compliant(
            "A\nB\nC\nD\n@FroxyDestekBOT", policy, "froxy"
        )
        self.assertEqual(len(text.splitlines()), 3)
        self.assertTrue(text.endswith(group_policy.PLAIN_FROXY_CTA))
        self.assertNotIn("@", text)
        self.assertIsNone(options["parse_mode"])

    def test_link_forbidden_lisansarena_has_only_plain_search_cta(self):
        policy = {**group_policy.DEFAULT_POLICY, "allow_urls": False,
                  "allow_deep_links": False, "allow_mentions": False}
        text, options = group_policy.make_policy_compliant(
            "Ürün listesi\nSipariş ve destek: @LisansArenaBot",
            policy,
            "lisansarena",
        )
        self.assertTrue(text.endswith(group_policy.PLAIN_LISANSARENA_CTA))
        self.assertIn("LisansArena ürün ve teslimat bilgisi", text)
        self.assertNotIn("KeyVadi", text)
        self.assertNotIn("@", text)
        self.assertNotIn("t.me", text)
        self.assertFalse(options["link_preview"])

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

    def test_kodkuponcek_policy_enforces_30_max_lines(self):
        entity = SimpleNamespace(id=999888777, username="kodkuponcek", default_banned_rights=None)
        _, policy = group_policy.resolve_group_policy("kodkuponcek", entity)
        self.assertEqual(policy["max_lines"], 30)
        self.assertTrue(policy["allow_urls"])
        self.assertTrue(policy["allow_mentions"])

        # Test with a 45-line message
        long_lines = [f"Line {i}: Product item info" for i in range(1, 45)]
        long_message = "\n".join(long_lines) + "\nSipariş ve güncel fiyat: @KeyVadiSatisBot"
        text, options = group_policy.make_policy_compliant(long_message, policy, "keyvadi")

        lines = text.splitlines()
        self.assertLessEqual(len(lines), 30)
        self.assertEqual(len(lines), 30)
        self.assertTrue(lines[-1].endswith("@KeyVadiSatisBot"))
        self.assertEqual(options["cta_mode"], "plain_mention")


if __name__ == "__main__":
    unittest.main()


