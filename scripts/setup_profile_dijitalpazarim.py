# -*- coding: utf-8 -*-
"""Set name, username, bio and photo for the new Dijital Pazarim ad account."""
import asyncio
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest, CheckUsernameRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest

sys.stdout.reconfigure(encoding='utf-8')
API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'
CANDIDATES = ['DijitalPazarim', 'DijitalPazarimm', 'DijitalPazarim_', 'DijitalPazarimTR',
              'DijitalPazarimOfficial', 'DijitalPazarim1', 'DijitalPazarimShop']
BIO = "Kupon, market kodlari, dijital lisans | Siparis: @DijitalPazarimBot"


async def main():
    session = open('dijitalpazarim_session_string.txt', encoding='utf-8').read().strip()
    client = TelegramClient(StringSession(session), API_ID, API_HASH)
    await client.connect()
    await client(UpdateProfileRequest(first_name='Dijital Pazarım', last_name='', about=BIO))
    print('Ad ve bio guncellendi')
    chosen = None
    for name in CANDIDATES:
        try:
            if await client(CheckUsernameRequest(name)):
                await client(UpdateUsernameRequest(name))
                chosen = name
                break
        except Exception as e:
            print('username denemesi', name, type(e).__name__)
    print('Kullanici adi:', chosen)
    f = await client.upload_file('static/dijitalpazarim_logo.jpg')
    await client(UploadProfilePhotoRequest(file=f))
    print('Profil fotografi yuklendi')
    me = await client.get_me()
    print('SONUC:', me.first_name, '@' + str(me.username), me.phone, 'id', me.id)
    await client.disconnect()

asyncio.run(main())
