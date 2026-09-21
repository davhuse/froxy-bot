import sys

with open('jarviscraft_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('SUPPORT_URL = "https://t.me/JarvisCraft"', 'SUPPORT_URL = "tg://user?id=32186"')
content = content.replace('SUPPORT_USERNAME = "JarvisCraft"', 'SUPPORT_USERNAME = "Geliþtirici (ID: 32186)"')

lines = content.split('\n')
new_lines = []
skip = False
for line in lines:
    if 'is_subbed = await is_user_subscribed(sender.id)' in line:
        skip = True
        new_lines.append('    # 1. ALWAYS show Gatekeeper to force Verify button')
        new_lines.append('    gate_msg = (')
        new_lines.append('        f"          ? **JARVISCRAFT\\'A HOÞ GELDÝNÝZ** ?\\n"')
        new_lines.append('        f"{LINE}\\n\\n"')
        new_lines.append('        f"Merhaba **{sender.first_name or \\'Deðerli Kullanýcý\\'}**,\\n\\n"')
        new_lines.append('        f"JarvisCraft bot ve yazýlým ekosistemini kullanabilmek için\\n"')
        new_lines.append('        f"resmi **Duyuru & Güncelleme Kanalýmýza** katýlmanýz gerekmektedir.\\n\\n"')
        new_lines.append('        f"?? **Kanalýmýzda Neler Var?**\\n"')
        new_lines.append('        f"{DOT}  Satýþa sunulan bot ve scriptlerin video demolarý\\n"')
        new_lines.append('        f"{DOT}  Açýk kaynak Python kodlarý ve hazýr kütüphaneler\\n"')
        new_lines.append('        f"{DOT}  Özel indirim kuponlarý ve VIP çekiliþler\\n"')
        new_lines.append('        f"{DOT}  API ve sistem güncellemeleri\\n\\n"')
        new_lines.append('        f"{LINE}\\n"')
        new_lines.append('        f"??  Aþaðýdaki butondan kanala katýlýn ve ardýndan **Doðrula**\\'ya týklayýn:"')
        new_lines.append('    )')
        new_lines.append('    await event.respond(gate_msg, buttons=get_gatekeeper_menu())')
        new_lines.append('    return')
        continue
    if skip and 'await event.respond(gate_msg, buttons=get_gatekeeper_menu())' in line:
        skip = False
        continue
    if skip and 'return' in line:
        skip = False
        continue
    if not skip:
        new_lines.append(line)

with open('jarviscraft_bot.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))
