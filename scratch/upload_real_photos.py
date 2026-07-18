import asyncio
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest

api_id = 31076280
api_hash = "7ba4072dcf0a05a7ccf80e570866b6d8"

accounts = [
    {
        "phone": "+6285191728354",
        "session": "1BVtsOG0Bu1GAAiu17AGLK79bqLss-2keFt0Kugqnq1HUT1QHrjA1Jp6WI-TUhG4bQqSb51U3IqJSs3deRrC1DSDAJAXsT_Lo9VI8WcqqRreP5eBYp4yKWV8sEipJ7DLkMZiKy-o0fpnBNvpVKCEHz12H0wkF72dmkngFjGTV84tKw5yUJfT3xumBc-k-lf7NFQhNWnSQagkZNwb4UGHk_umO6ZcvZrBiu-1NdubZ4nUlI0LFmQ5wA3WQsISS1WVZoFBkmcEIjXtRVb7ygjB_7Zmx3Mr6v_TabgycCthAYMox61RTzZSTU686_bXbPpq_Dgrp50hgfj-Wp-S6UWK1A2MHJxPlyH4=",
        "brand": "KeyVadi",
        "photo": r"C:\Users\habil\Downloads\keyvadi-icon_500KB (1).jpg",
    },
    {
        "phone": "+13412648927",
        "session": "1AZWarzsBuyAiCinDXh9__cCrDW0v3_s7zFaKzpygVSlkMgV3QEKHAtoRcb9zWetfi-F3Wsbb6lF8yCMsPPEdKDGI9q-Ojf5HmK-GZVlrDpl65za7Ryou5Vx7L9jyX8jiwBpJ8LDkH4qg2l5pT-IQQqtPfFyaPwGfp-kIgzpHCvI0YzQy27Gk0xDsz8syrSulTiZ8dFsJW8sxI4pHUOerilaOFmv6ChOee7ZBBdXN_bm75f0Tg__UwxXOz0NSTWqYyqTiodBeHvFVVGq5eQAwZCUDTcQsTktRhzxrBQ3pP6twIpeTSQKtuuJ_YvJ5WVQ_No3b27TOFajGHuNu_9MZBSh2qxN13ls=",
        "brand": "LisansArena",
        "photo": r"C:\Users\habil\Downloads\LisansArena_logo_with_badges_202607132230.jpeg",
    },
]

async def update_photo(acc):
    phone = acc["phone"]
    print(f"[{phone} - {acc['brand']}] Baglaniyor...")
    client = TelegramClient(StringSession(acc["session"]), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print(f"[{phone}] YETKISIZ! Atlanıyor.")
        await client.disconnect()
        return

    # Delete old photos first
    print(f"[{phone}] Eski profil fotograflari siliniyor...")
    try:
        photos = await client.get_profile_photos("me")
        if photos:
            await client(DeletePhotosRequest(photos))
            print(f"[{phone}] {len(photos)} eski foto silindi.")
        else:
            print(f"[{phone}] Eski foto yok.")
    except Exception as e:
        print(f"[{phone}] Silme hatasi: {e}")

    # Upload new photo
    print(f"[{phone}] Yeni profil fotografı yukleniyor: {acc['photo']}")
    try:
        uploaded = await client.upload_file(acc["photo"])
        await client(UploadProfilePhotoRequest(file=uploaded))
        print(f"[{phone}] [{acc['brand']}] [OK] Profil fotografı yuklendi!")
    except Exception as e:
        print(f"[{phone}] Yukleme hatasi: {e}")

    await client.disconnect()

async def main():
    for acc in accounts:
        await update_photo(acc)
        print("-" * 50)

asyncio.run(main())
