# -*- coding: utf-8 -*-
import os
import sys

with open("froxy_bot.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

new_lines = []
skip = False
for idx, line in enumerate(lines):
    if idx == 823 and "reply_prefix" in line:
        new_lines.append('        "reply_prefix": "📨 **KeyVadi Destek Ekibinden Cevap:**\\n\\n",\n')
        new_lines.append('        "choose_lang": "Lütfen dilinizi seçin / Please choose your language:"\n')
        new_lines.append('    }\n')
        new_lines.append('}\n\n')
        new_lines.append('# Main Menu Helper — Streamlined Mini App First Experience\n')
        new_lines.append('async def show_main_menu(event, user_id, is_callback=False):\n')
        new_lines.append('    welcome = (\n')
        new_lines.append('        "⚡ **KEYVADI PRO — Dijital Lisans & E-Pin Mağazası**\\n"\n')
        new_lines.append('        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"\n')
        new_lines.append('        "🎉 **KeyVadi\'ye Hoş Geldiniz!**\\n\\n"\n')
        new_lines.append('        "Netflix, ChatGPT Plus, Canva Pro, Gemini, Xbox Game Pass, FC26, Steam Key ve tüm lisanslar **%70 indirimli** ve **7/24 anında otomatik teslimatla** KeyVadi Mini App\'te!\\n\\n"\n')
        new_lines.append('        "👇 **Alışverişe başlamak ve bakiyenizi yönetmek için tıklayın:**"\n')
        new_lines.append('    )\n')
        new_lines.append('    buttons = [\n')
        new_lines.append('        [Button.url("🚀 KeyVadi Mağazasını Aç (Mini App)", KEYVADI_MINI_APP_URL)],\n')
        new_lines.append('        [\n')
        new_lines.append('            Button.url("💳 Bakiye Yükle", f"{KEYVADI_MINI_APP_URL}#walletTab"),\n')
        new_lines.append('            Button.url("🎁 %10 Nakit Kazan", f"{KEYVADI_MINI_APP_URL}#referralTab")\n')
        new_lines.append('        ],\n')
        new_lines.append('        [\n')
        new_lines.append('            Button.url("💬 Canlı Destek (@KeyVadiDestek)", "https://t.me/KeyVadiDestek")\n')
        new_lines.append('        ]\n')
        new_lines.append('    ]\n')
        new_lines.append('    if is_callback:\n')
        new_lines.append('        await safe_event_edit(event, welcome, buttons=buttons)\n')
        new_lines.append('    else:\n')
        new_lines.append('        await event.respond(welcome, buttons=buttons)\n\n')
        skip = True
    elif skip:
        if "@bot.on(events.CallbackQuery(data=b'menu_verify_payment'))" in line:
            skip = False
            new_lines.append(line)
    else:
        new_lines.append(line)

with open("froxy_bot.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("[✓] froxy_bot.py başarıyla güncellendi ve sözdizimi düzeltildi!")
