# -*- coding: utf-8 -*-
"""Check SpamBot status and set profile picture on +18595173039 account."""

import asyncio
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.photos import UploadProfilePhotoRequest

sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open('dijitalpazarim_session_string.txt', 'r', encoding='utf-8') as f:
    session_str = f.read().strip()

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    me = await client.get_me()
    print(f"Bağlanıldı: {me.first_name} {me.last_name or ''} (@{me.username}) - {me.phone}")
    
    # 1. Set Profile Photo for the User Account (+18595173039)
    try:
        print("\nHesap profil fotoğrafı yükleniyor...")
        upload_file = await client.upload_file("static/dijitalpazarim_logo.jpg")
        await client(UploadProfilePhotoRequest(file=upload_file))
        print("Hesap profil fotoğrafı başarıyla Dijital Pazarım logosu yapıldı!")
    except Exception as e:
        print(f"Profil fotoğrafı güncelleme hatası: {e}")
        
    # 2. Check SpamBot status
    try:
        print("\nSpamBot durumu kontrol ediliyor...")
        await client.send_message("SpamBot", "/start")
        await asyncio.sleep(3)
        async for msg in client.iter_messages("SpamBot", limit=1):
            print(f"SpamBot Yanıtı:\n{msg.text}")
    except Exception as e:
        print(f"SpamBot sorgulama hatası: {e}")
        
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
