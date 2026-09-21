# -*- coding: utf-8 -*-
import re
with open('jarviscraft_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = re.compile(r'    # 1\. Check Channel Subscription \(Gatekeeper\)\n    is_subbed = await is_user_subscribed\(sender\.id\)\n    if not is_subbed:\n        gate_msg = \(\n(?:.*?\n)+?        \)\n        await event\.respond\(gate_msg, buttons=get_gatekeeper_menu\(\)\)\n        return', re.MULTILINE)

new_block = '''    # 1. Her zaman Gatekeeper mesajini goster
    gate_msg = (
        f"          ⚡ **JARVISCRAFT\\'A HOŞ GELDİNİZ** ⚡\\n"
        f"{LINE}\\n\\n"
        f"Merhaba **{sender.first_name or \\'Değerli Kullanıcı\\'}**,\\n\\n"
        f"JarvisCraft bot ve yazılım ekosistemini kullanabilmek için\\n"
        f"resmi **Duyuru & Güncelleme Kanalımıza** katılmanız gerekmektedir.\\n\\n"
        f"📢 **Kanalımızda Neler Var?**\\n"
        f"{DOT}  Satışa sunulan bot ve scriptlerin video demoları\\n"
        f"{DOT}  Açık kaynak Python kodları ve hazır kütüphaneler\\n"
        f"{DOT}  Özel indirim kuponları ve VIP çekilişler\\n"
        f"{DOT}  API ve sistem güncellemeleri\\n\\n"
        f"{LINE}\\n"
        f"👇  Aşağıdaki butondan kanala katılın ve ardından **Doğrula**\\'ya tıklayın:"
    )
    await event.respond(gate_msg, buttons=get_gatekeeper_menu())
    return'''

content = pattern.sub(new_block, content)

with open('jarviscraft_bot.py', 'w', encoding='utf-8') as f:
    f.write(content)
