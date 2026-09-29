# -*- coding: utf-8 -*-
"""Complete login with the code received for +18595173039."""

import asyncio
import json
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def main():
    if len(sys.argv) < 2:
        print("Kullanım: python scripts/complete_auth_dijitalpazarim.py <DOGRULAMA_KODU> [2FA_SIFRESI]")
        sys.exit(1)
        
    code = sys.argv[1].strip()
    password = sys.argv[2].strip() if len(sys.argv) > 2 else None
    
    with open('temp_dp_auth.json', 'r', encoding='utf-8') as f:
        auth_data = json.load(f)
        
    phone = auth_data['phone']
    phone_code_hash = auth_data['phone_code_hash']
    session_str = auth_data['session']
    
    print(f"{phone} için giriş yapılıyor (Kod: {code})...")
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
    except Exception as e:
        if "Two-steps verification" in str(e) or "password" in str(type(e).__name__).lower():
            if not password:
                print("2FA_REQUIRED: Bu hesapta 2 Adımlı Doğrulama (2FA şifresi) aktif. Lütfen 2FA şifrenizi de iletin.")
                sys.exit(2)
            else:
                print("2FA şifresi deneniyor...")
                await client.sign_in(password=password)
        else:
            print(f"Giriş hatası: {e}")
            sys.exit(1)
            
    final_session = client.session.save()
    me = await client.get_me()
    print("\nGİRİŞ BAŞARILI!")
    print(f"Hesap: {me.first_name} {me.last_name or ''} (@{me.username or 'Kullanıcı adı yok'})")
    print(f"Telefon: {me.phone}")
    
    with open("dijitalpazarim_session_string.txt", "w", encoding="utf-8") as f:
        f.write(final_session)
        
    print("\nSession string başarıyla 'dijitalpazarim_session_string.txt' dosyasına kaydedildi!")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
