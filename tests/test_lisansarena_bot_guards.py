import ast
from pathlib import Path
import unittest


SOURCE = Path("lisansarena_bot.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


class LisansArenaBotGuardTests(unittest.TestCase):
    def test_all_text_commands_have_one_time_event_guard(self):
        command_handlers = {
            "start_handler": "start",
            "store_handler": "magaza",
            "products_handler": "urunler",
            "balance_handler": "bakiye",
            "orders_handler": "siparisler",
            "accounts_handler": "hesaplar",
            "history_handler": "gecmis",
            "guides_handler": "kullanim",
            "request_handler": "talep",
            "support_handler": "destek",
            "refund_handler": "iade",
            "referral_handler": "referans",
            "draws_handler": "cekilis",
            "settings_handler": "ayarlar_dil",
            "help_handler": "yardim",
        }
        functions = {
            node.name: node
            for node in TREE.body
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
        }
        for name, command in command_handlers.items():
            decorators = functions[name].decorator_list
            guarded = [
                node for node in decorators
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "once_per_command"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == command
            ]
            self.assertEqual(1, len(guarded), name)

    def test_profile_configuration_is_opt_in_and_menu_is_canonical(self):
        self.assertIn('LISANSARENA_CONFIGURE_PROFILE', SOURCE)
        self.assertIn('https://froxy-bot-live.onrender.com/la/app/', SOURCE)
        self.assertIn('MINI_APP_URL = (_configured_mini_app_url or _canonical_mini_app_url)', SOURCE)

    def test_generic_private_handler_does_not_answer_commands(self):
        self.assertIn('or (event.raw_text or "").startswith("/")', SOURCE)


if __name__ == "__main__":
    unittest.main()
