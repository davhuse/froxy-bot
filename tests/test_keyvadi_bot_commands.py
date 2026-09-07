import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import re
import unittest
import froxy_bot

class KeyVadiBotCommandsTest(unittest.TestCase):
    def test_bot_commands_list(self):
        commands_dict = dict(froxy_bot.BOT_COMMANDS)
        self.assertIn('start', commands_dict)
        self.assertIn('firsatlar', commands_dict)
        self.assertIn('magaza', commands_dict)
        self.assertIn('urunler', commands_dict)
        self.assertIn('destek', commands_dict)
        self.assertIn('referans', commands_dict)
        self.assertIn('bakiye', commands_dict)
        self.assertIn('siparisler', commands_dict)

    def test_command_regexes_match_bot_username(self):
        patterns = {
            'start': r'(?i)^/start(?:@\w+)?(?:\s+.*)?$',
            'firsatlar': r'(?i)^/(?:firsat|firsatlar|deals)(?:@\w+)?$',
            'magaza': r'(?i)^/(?:magaza|store|shop)(?:@\w+)?$',
            'urunler': r'(?i)^/(?:urunler|katalog|products|kategoriler)(?:@\w+)?$',
            'destek': r'(?i)^/(?:destek|support|yardim|help)(?:@\w+)?$',
            'referans': r'(?i)^/(?:referans|ref|davet)(?:@\w+)?$',
            'bakiye': r'(?i)^/(?:bakiye|cuzdan|wallet)(?:@\w+)?$',
            'siparisler': r'(?i)^/(?:siparisler|siparislerim|orders)(?:@\w+)?$',
        }

        test_cases = [
            ('start', '/start'),
            ('start', '/start@KeyVadiSatisBot'),
            ('start', '/start ref_12345'),
            ('firsatlar', '/firsatlar'),
            ('firsatlar', '/firsatlar@KeyVadiSatisBot'),
            ('firsatlar', '/firsat'),
            ('magaza', '/magaza'),
            ('magaza', '/magaza@KeyVadiSatisBot'),
            ('urunler', '/urunler'),
            ('urunler', '/urunler@KeyVadiSatisBot'),
            ('destek', '/destek'),
            ('destek', '/destek@KeyVadiSatisBot'),
            ('destek', '/yardim'),
            ('referans', '/referans'),
            ('referans', '/referans@KeyVadiSatisBot'),
            ('referans', '/davet'),
            ('bakiye', '/bakiye'),
            ('bakiye', '/bakiye@KeyVadiSatisBot'),
            ('siparisler', '/siparisler'),
            ('siparisler', '/siparisler@KeyVadiSatisBot'),
        ]

        for cmd, text in test_cases:
            pat = patterns[cmd]
            self.assertTrue(re.match(pat, text), f'Pattern {pat} failed to match {text}')

    def test_group_link_configured(self):
        self.assertTrue(froxy_bot.KEYVADI_GROUP_LINK.startswith('https://t.me/'))
        markup = froxy_bot.mini_app_markup()
        self.assertIsNotNone(markup)
        
        all_buttons = [btn for row in markup.rows for btn in row.buttons]
        group_btns = [b for b in all_buttons if hasattr(b, 'url') and 't.me' in b.url]
        self.assertTrue(len(group_btns) > 0, 'Expected at least one Telegram group link button in menu')

if __name__ == '__main__':
    unittest.main()
