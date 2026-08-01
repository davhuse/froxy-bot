import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

file_path = "lisansarena_bot.py"

with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update product_footer and buy_btn in TEXTS
code = code.replace('"buy_btn": "💳 Güvenle Ödeme Yap (Shopier)"', '"buy_btn": "💳 IBAN Bilgileri ile Satın Al"')
code = code.replace('"buy_btn": "💳 Pay Securely (Shopier)"', '"buy_btn": "💳 Pay via Bank IBAN Transfer"')
code = code.replace(
    '"product_footer": "✅ Güvenli İşlem · ⚡ Hızlı Teslimat · 🤝 Kesintisiz Destek\\n\\nÜrünü satın almak için aşağıdaki güvenli ödeme butonunu kullanabilirsiniz."',
    '"product_footer": "✅ Güvenli Havale/EFT Ödemesi · ⚡ Hızlı Teslimat · 🤝 Kesintisiz Destek\\n\\nÜrünü satın almak için aşağıdaki IBAN ödeme butonunu kullanabilirsiniz."'
)

# 2. Add IBAN constants if missing
iban_block = '''
IBAN_NO = "TR570008291009491531109206"
IBAN_ALICI = "Mahmut Rençber"
IBAN_UYARI = "🔴 **ÖNEMLİ UYARI:** Havale / EFT ödemesi yaparken **AÇIKLAMA alanını KESİNLİKLE BOŞ BIRAKINIZ!** Açıklama kısmına hiçbir şey yazmayınız."
'''

if "IBAN_NO =" not in code:
    code = code.replace('BOT_TOKEN = config.get', iban_block + '\nBOT_TOKEN = config.get')

# 3. Product detail page buttons replacement
old_prod_buttons = '''    cat_title = t["cat_title_mapping"].get(cat_key_found, CATEGORIES[cat_key_found]['title'])
    buttons = [
        [Button.url(t["buy_btn"], shopier_url)],
        [Button.inline(f"↩️ {cat_title}", f"cat_{cat_key_found}".encode())],
        [Button.inline(t["main_menu"], b"menu_main")]
    ]'''

new_prod_buttons = '''    cat_title = t["cat_title_mapping"].get(cat_key_found, CATEGORIES[cat_key_found]['title'])
    buttons = [
        [Button.inline("💳 IBAN Bilgileri & Satın Al", f"iban_{prod_key}".encode())],
        [Button.inline("📸 Ödemeyi Doğrula (Dekont Gönder)", f"verify_iban_{prod_key}".encode())],
        [Button.inline(f"↩️ {cat_title}", f"cat_{cat_key_found}".encode())],
        [Button.inline(t["main_menu"], b"menu_main")]
    ]'''

code = code.replace(old_prod_buttons, new_prod_buttons)

# 4. Add IBAN info & verify callbacks before # Support Menu
iban_callbacks = '''
# IBAN Ödeme Bilgileri Gösterici
@bot.on(events.CallbackQuery(pattern=r'iban_(\\w+)'))
async def iban_info_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    user_id = event.sender_id
    lang = user_lang_helper.get_user_lang(user_id) or "tr"
    prod_key = event.data.decode('utf-8').replace("iban_", "")
    
    product = None
    cat_key_found = None
    for ck, cat in CATEGORIES.items():
        if prod_key in cat["products"]:
            product = cat["products"][prod_key]
            cat_key_found = ck
            break
            
    title = product['title'] if product else "Seçilen Ürün"
    price = product['price'] if product else "0 TL"
    
    if lang == "en":
        price = user_lang_helper.convert_price_to_usd(price)

    iban_text = (
        f"💳 **LisansArena IBAN Ödeme Bilgileri**\\n\\n"
        f"📦 **Satın Alınacak Ürün:** {title}\\n"
        f"💰 **Ödenecek Tutar:** `{price}`\\n\\n"
        f"🏦 **IBAN:**\\n`{IBAN_NO}`\\n\\n"
        f"👤 **Alıcı Adı Soyadı:**\\n`{IBAN_ALICI}`\\n\\n"
        f"{IBAN_UYARI}\\n\\n"
        f"Ödemenizi yaptıktan sonra aşağıdaki **'📸 Ödemeyi Doğrula / Dekont Gönder'** butonuna tıklayarak dekont fotoğrafını bu sohbete gönderebilirsiniz.\\n\\n"
        f"💬 **Destek / İletişim:** @LisansArenaAdmin"
    )
    buttons = [
        [Button.inline("📸 Ödemeyi Doğrula (Dekont Gönder)", f"verify_iban_{prod_key}".encode())],
        [Button.inline("↩️ Ürün Sayfasına Dön", f"prod_{prod_key}".encode())],
        [Button.inline("🏠 Ana Menü", b"menu_main")]
    ]
    await event.edit(iban_text, buttons=buttons)

# Dekont Bekleme Durumu Başlatıcı
@bot.on(events.CallbackQuery(pattern=r'verify_iban_(\\w+)'))
async def verify_iban_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    user_id = event.sender_id
    prod_key = event.data.decode('utf-8').replace("verify_iban_", "")
    user_states[user_id] = f"AWAITING_DEKONT:{prod_key}"
    
    text = (
        "📸 **Ödeme Doğrulama & Dekont Gönderimi**\\n\\n"
        "Lütfen Havale/EFT ödemenize ait **dekont fotoğrafını veya ekran görüntüsünü** bu sohbete gönderin.\\n\\n"
        "Ödeme ve dekontunuz yetkili ekibimize anında iletilecek ve lisans kodunuz bu sohbet üzerinden tarafınıza teslim edilecektir.\\n\\n"
        "💬 İletişim / Canlı Destek: @LisansArenaAdmin\\n"
        "*(Vazgeçmek için /start yazabilirsiniz)*"
    )
    buttons = [
        [Button.inline("↩️ Vazgeç ve Ana Menü", b"menu_main")]
    ]
    await event.edit(text, buttons=buttons)
'''

if "async def iban_info_handler" not in code:
    code = code.replace("# Support Menu", iban_callbacks + "\n# Support Menu")

# 5. Handle dekont message upload in message_handler
old_handler_start = '''    if user_states.get(user_id) == "AWAITING_VERIFY_PAYMENT_INFO":'''

dekont_message_logic = '''    # Dekont Fotoğrafı Gönderimi İnceleyicisi
    current_state = str(user_states.get(user_id) or "")
    if current_state.startswith("AWAITING_DEKONT") or (event.message.media and user_states.get(user_id) != "AWAITING_SUPPORT"):
        if event.text and event.text.startswith('/'):
            user_states[user_id] = None
            return
            
        prod_key = current_state.split(":", 1)[1] if ":" in current_state else ""
        product = None
        for ck, cat in CATEGORIES.items():
            if prod_key in cat["products"]:
                product = cat["products"][prod_key]
                break
                
        prod_title = product['title'] if product else "Belirtilmedi / Genel Ürün"
        prod_price = product['price'] if product else "0 TL"
        
        user = await event.get_sender()
        username = f"@{user.username}" if user and getattr(user, 'username', None) else "Yok"
        first_name = getattr(user, 'first_name', '') or ""
        last_name = getattr(user, 'last_name', '') or ""
        
        admin_caption = (
            f"📸 **[LisansArena] YENİ IBAN ÖDEMESİ & DEKONT BİLDİRİMİ!**\\n"
            f"👤 **Kullanıcı ID:** `{user_id}`\\n"
            f"👤 **Adı Soyadı:** {first_name} {last_name}\\n"
            f"💬 **Kullanıcı Adı:** {username}\\n"
            f"📦 **Satın Alınan Ürün:** {prod_title}\\n"
            f"💰 **Tutar:** {prod_price}\\n"
            f"🏦 **IBAN:** `{IBAN_NO}` ({IBAN_ALICI})\\n"
            f"--------------------------------------\\n"
            f"*(Dekont resmi yukarıdadır. Kullanıcıya lisans göndermek veya yanıtlamak için bu mesajı Reply ederek yazabilirsiniz.)*"
        )
        admin_buttons = [[Button.inline("🚫 Kullanıcıyı Engelle (Ban)", f"la_adm_ban_{user_id}".encode())]]
        
        try:
            if event.message.media:
                await bot.send_file(ADMIN_ID, event.message.media, caption=admin_caption, buttons=admin_buttons)
            else:
                await bot.send_message(ADMIN_ID, f"{admin_caption}\\n\\n💬 **Müşteri Notu:** {event.text}", buttons=admin_buttons)
                
            await event.respond(
                "✅ **Ödeme Dekontunuz Başarıyla Alındı!**\\n\\n"
                f"📦 **Ürün:** {prod_title}\\n"
                f"💰 **Tutar:** {prod_price}\\n\\n"
                "Ödemeniz ve dekontunuz yetkili ekibimize iletildi. İncelendikten sonra lisans bilgileriniz bu sohbet üzerinden tarafınıza iletilecektir. 😊\\n\\n"
                "💬 İletişim / Canlı Destek için: @LisansArenaAdmin"
            )
            save_ticket_to_file("LisansArena_IBAN_Dekont", user_id, first_name, last_name, username, f"DEKONT: {prod_title} ({prod_price})")
        except Exception as e:
            logger.error(f"Failed to process dekont for user {user_id}: {e}")
            await event.respond("⚠️ Dekont gönderilirken bir sorun oluştu. Lütfen tekrar deneyin veya @LisansArenaAdmin adresinden iletişime geçin.")
            
        user_states[user_id] = None
        return

'''

if "AWAITING_DEKONT" not in code:
    code = code.replace(old_handler_start, dekont_message_logic + old_handler_start)

# 6. Update smart matching response to show IBAN button instead of Shopier
old_match_buttons = '''                buttons = [
                    [Button.url(t["buy_btn"], matched_product.get('url', 'https://www.shopier.com/lisansarena'))],
                    [Button.inline(t["support_btn"], b"menu_support")],
                    [Button.inline("📋 Ana Menü / Main Menu", b"menu_main")]
                ]'''

new_match_buttons = '''                buttons = [
                    [Button.inline("💳 IBAN Bilgileri & Satın Al", f"iban_{matched_product['id']}".encode())],
                    [Button.inline("📸 Ödemeyi Doğrula (Dekont Gönder)", f"verify_iban_{matched_product['id']}".encode())],
                    [Button.inline(t["support_btn"], b"menu_support")],
                    [Button.inline("📋 Ana Menü / Main Menu", b"menu_main")]
                ]'''

code = code.replace(old_match_buttons, new_match_buttons)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code)

print("SUCCESS: LisansArena bot successfully patched for IBAN payment & dekont verification!")
