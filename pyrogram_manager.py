import os
from pyrogram import Client

# Telegram Desktop Genel (Leaked) API değerleri
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"

# Aktif istemcileri (client) bellekte tutmak için sözlük
# İleride veritabanı ile eşleştirilebilir.
active_clients = {}

async def create_client(telegram_id: int):
    # Her kullanıcı için ayrı bir session dosyası oluşturur
    session_name = f"sessions/user_{telegram_id}"
    
    # sessions klasörü yoksa oluştur
    if not os.path.exists("sessions"):
        os.makedirs("sessions")

    client = Client(
        name=session_name,
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=False
    )
    
    active_clients[telegram_id] = client
    return client

async def send_auth_code(telegram_id: int, phone_number: str):
    client = await create_client(telegram_id)
    await client.connect()
    try:
        sent_code_info = await client.send_code(phone_number)
        return {"status": "success", "phone_code_hash": sent_code_info.phone_code_hash, "client": client}
    except Exception as e:
        await client.disconnect()
        return {"status": "error", "message": str(e)}

async def sign_in_with_code(telegram_id: int, phone_number: str, phone_code_hash: str, phone_code: str):
    client = active_clients.get(telegram_id)
    if not client:
        return {"status": "error", "message": "Oturum bulunamadı. Lütfen numarayı tekrar girin."}
    
    try:
        await client.sign_in(phone_number, phone_code_hash, phone_code)
        # Giriş başarılıysa session dosyası otomatik kaydedilir (in_memory=False)
        await client.disconnect()
        del active_clients[telegram_id]
        return {"status": "success"}
    except Exception as e:
        await client.disconnect()
        del active_clients[telegram_id]
        return {"status": "error", "message": str(e)}
