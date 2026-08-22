import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

import database
import pyrogram_manager

logging.basicConfig(level=logging.INFO)
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

database.init_db()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Durumlar (FSM)
class PaymentState(StatesGroup):
    waiting_for_amount = State()

class AccountState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()

def get_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Bakiye Yükle", callback_data="menu_add_balance")
    builder.button(text="📱 Hesaplarım", callback_data="menu_accounts")
    builder.button(text="📝 Reklam Mesajları", callback_data="menu_messages")
    builder.button(text="🚀 Gönderimi Başlat", callback_data="menu_start_posting")
    builder.adjust(2, 2)
    return builder.as_markup()

@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    user = database.get_user(message.from_user.id)
    text = (
        f"👋 Merhaba {message.from_user.first_name}!\n\n"
        f"Oto-Reklam Paneline Hoş Geldin.\n"
        f"Mevcut Bakiyen: <b>{user.balance} TL</b>\n\n"
        f"Lütfen yapmak istediğiniz işlemi seçin:"
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")

# --- BAKİYE EKLEME ---
@dp.callback_query(F.data == "menu_add_balance")
async def process_add_balance(callback: types.CallbackQuery, state: FSMContext):
    text = (
        "💳 <b>Bakiye Yükleme (Havale/EFT)</b>\n\n"
        "Lütfen yatırmak istediğiniz tutarı TL cinsinden sadece rakam olarak yazın. (Örn: 100)"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await state.set_state(PaymentState.waiting_for_amount)
    await callback.answer()

@dp.message(PaymentState.waiting_for_amount)
async def process_payment_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Lütfen geçerli bir tutar girin. (Örn: 50)")
        return

    text = (
        f"✅ <b>Tutar Alındı:</b> {amount} TL\n\n"
        "Aşağıdaki IBAN numarasına gönderimi yapıp açıklama kısmına Telegram ID'nizi yazın.\n\n"
        "🏦 <b>Banka:</b> Enpara\n"
        "👤 <b>Alıcı:</b> Haxsoft Destek\n"
        "💳 <b>IBAN:</b> TR00 0000 0000 0000 0000 0000 00\n"
        f"🆔 <b>Açıklama:</b> {message.from_user.id}\n\n"
        "Ödemeniz onaylandığında bakiyeniz otomatik yüklenecektir."
    )
    await message.answer(text, parse_mode="HTML")
    await state.clear()

# --- HESAP EKLEME (USERBOT) ---
@dp.callback_query(F.data == "menu_accounts")
async def process_accounts(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yeni Hesap Ekle", callback_data="add_new_account")
    builder.button(text="🔙 Ana Menü", callback_data="go_main")
    builder.adjust(1)
    
    await callback.message.edit_text("📱 <b>Hesap Yönetimi</b>\n\nSisteme bağlı reklam hesaplarınızı buradan yönetebilirsiniz.", reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "go_main")
async def process_go_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await start_cmd(callback.message, state)
    await callback.answer()

@dp.callback_query(F.data == "add_new_account")
async def add_new_account(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📞 Lütfen hesabınızın telefon numarasını uluslararası formatta yazın (Örn: +12237587384 veya +905321234567)")
    await state.set_state(AccountState.waiting_for_phone)
    await callback.answer()

@dp.message(AccountState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone_number = message.text.strip()
    
    msg = await message.answer("⏳ Telegram'a bağlanılıyor, lütfen bekleyin...")
    
    result = await pyrogram_manager.send_auth_code(message.from_user.id, phone_number)
    
    if result["status"] == "success":
        await state.update_data(phone_number=phone_number, phone_code_hash=result["phone_code_hash"])
        await msg.edit_text(
            "✅ Telegram'dan telefonunuza bir doğrulama kodu gönderildi.\n\n"
            "🚨 <b>DİKKAT:</b> Güvenlik sebebiyle Telegram direkt yazılan kodları engeller (Kod paylaşıldı hatası verir).\n\n"
            "Bu engeli aşmak için kodu <b>TERSTEN</b> yazmalısınız.\n"
            "<i>Örneğin, kodunuz <b>12345</b> ise buraya <b>54321</b> olarak yazmalısınız.</i>\n\n"
            "Lütfen kodunuzu <b>TERSTEN</b> buraya yazın:",
            parse_mode="HTML"
        )
        await state.set_state(AccountState.waiting_for_code)
    else:
        await msg.edit_text(f"❌ Kod gönderilirken bir hata oluştu:\n{result['message']}\n\nLütfen numarayı kontrol edip tekrar girin.")

@dp.message(AccountState.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    # Telegram engeline takılmamak için tersten alınan kodu tekrar düze çeviriyoruz
    raw_text = message.text.replace(" ", "").replace("-", "").strip()
    phone_code = raw_text[::-1]
    data = await state.get_data()
    
    msg = await message.answer("⏳ Kod doğrulanıyor...")
    
    result = await pyrogram_manager.sign_in_with_code(
        message.from_user.id, 
        data["phone_number"], 
        data["phone_code_hash"], 
        phone_code
    )
    
    if result["status"] == "success":
        await msg.edit_text("🎉 Harika! Hesabınız sisteme başarıyla bağlandı.\nArtık bu hesap üzerinden gruplara otomatik mesaj gönderebilirsiniz.")
        await state.clear()
    else:
        await msg.edit_text(f"❌ Giriş başarısız:\n{result['message']}\n\nTekrar denemek için numarayı baştan girin.")
        await state.set_state(AccountState.waiting_for_phone)

@dp.callback_query(F.data.in_(["menu_messages", "menu_start_posting"]))
async def not_implemented(callback: types.CallbackQuery):
    await callback.answer("⏳ Bu bölüm yapım aşamasındadır.", show_alert=True)

async def main():
    if not BOT_TOKEN:
        logging.error("Lütfen .env dosyasına geçerli bir BOT_TOKEN girin.")
        return

    print("Bot başlatılıyor...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
