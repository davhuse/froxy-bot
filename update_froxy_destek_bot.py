import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

file_path = "froxy_destek_bot.py"

with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

# Replace product list & package buttons in froxy_destek_bot.py
old_texts_tr = '''        "pkg_btn_list": [
            ("🚀 Başlangıç — 5K Kredi (₺129.99)", "pkg_baslangic"),
            ("⭐ Popüler — 15K Kredi (₺249.99)", "pkg_populer"),
            ("💼 Profesyonel — 50K Kredi (₺449.99)", "pkg_profesyonel")
        ],'''

new_texts_tr = '''        "pkg_btn_list": [
            ("🤖 Gemini Pro 12 Ay Davet (₺59.99)", "pkg_gemini_12m"),
            ("🤖 Gemini Pro 18 Ay Davet (₺99.99)", "pkg_gemini_18m"),
            ("🚀 Gemini Pro + Antigravity 12 Ay (₺169.99)", "pkg_gemini_anti_12m"),
            ("🚀 Gemini Pro + Antigravity 18 Ay (₺249.99)", "pkg_gemini_anti_18m"),
            ("💬 ChatGPT Plus Kişisel (₺499.90)", "pkg_chatgpt_kisisel"),
            ("💬 ChatGPT Plus Ortak (₺39.99)", "pkg_chatgpt_ortak"),
            ("💻 ChatGPT Plus + Codex (₺599.90)", "pkg_chatgpt_codex"),
            ("📱 Codex SMS Doğrulama Kodu (₺29.99)", "pkg_codex_sms"),
            ("💎 Gemini Ultra Kredisiz (₺299.99)", "pkg_gemini_ultra_kredisiz"),
            ("💎 Gemini Ultra 2500 Kredili (₺399.99)", "pkg_gemini_ultra_25k"),
            ("⚡ ChatGPT Go 3 Aylık Kod (₺49.99)", "pkg_chatgpt_go"),
            ("🔍 Perplexity Pro 1 Aylık Ortak (₺69.99)", "pkg_perplexity_ortak")
        ],'''

code = code.replace(old_texts_tr, new_texts_tr)

# Replace welcome message
old_welcome = '''            "🤖 **Froxy AI Destek Paneline Hoş Geldiniz!**\\n\\n"
            "ChatGPT, Claude, Gemini ve 1100+ AI modelini tek panelden kullanmanızı sağlayan "
            "kredi paketlerimiz en uygun fiyatlarla burada!\\n\\n"
            "🌐 **Web Sitemiz:** froxyai.com\\n\\n"
            "Lütfen yapmak istediğiniz işlemi seçin 👇"'''

new_welcome = '''            "⚡ **Froxy AI Mağaza & Destek Paneline Hoş Geldiniz!**\\n\\n"
            "Birden fazla yapay zeka aracına para vermek yerine, hepsini tek panelden kullanabilirsiniz!\\n"
            "GPT, Claude Sonnet 5, Gemini 3.5 Flash, DeepSeek V4 ve 1.100+ model aynı altyapıda.\\n\\n"
            "🌐 **Web Sitemiz:** https://froxyai.com\\n\\n"
            "Lütfen incelemek veya satın almak istediğiniz ürünü seçin 👇"'''

code = code.replace(old_welcome, new_welcome)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code)

print("SUCCESS: Updated froxy_destek_bot.py with clean Froxy AI product list!")
