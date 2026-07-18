import asyncio
import os
os.environ["PYTHONIOENCODING"] = "utf-8"

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.account import SetPrivacyRequest as UpdatePrivacyRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.types import (
    InputPrivacyValueDisallowAll,
    InputPrivacyValueAllowAll,
    InputPrivacyValueAllowContacts,
    InputPrivacyKeyChatInvite,
    InputPrivacyKeyPhoneNumber,
    InputPrivacyKeyStatusTimestamp,
    InputPrivacyKeyProfilePhoto,
    InputPrivacyKeyForwards,
    InputPrivacyKeyPhoneCall,
)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

accounts = [
    {
        "phone": "+6285191728354",
        "session": "1BVtsOG0Bu1GAAiu17AGLK79bqLss-2keFt0Kugqnq1HUT1QHrjA1Jp6WI-TUhG4bQqSb51U3IqJSs3deRrC1DSDAJAXsT_Lo9VI8WcqqRreP5eBYp4yKWV8sEipJ7DLkMZiKy-o0fpnBNvpVKCEHz12H0wkF72dmkngFjGTV84tKw5yUJfT3xumBc-k-lf7NFQhNWnSQagkZNwb4UGHk_umO6ZcvZrBiu-1NdubZ4nUlI0LFmQ5wA3WQsISS1WVZoFBkmcEIjXtRVb7ygjB_7Zmx3Mr6v_TabgycCthAYMox61RTzZSTU686_bXbPpq_Dgrp50hgfj-Wp-S6UWK1A2MHJxPlyH4=",
        "brand": "KeyVadi",
        "first_name": "KeyVadi",
        "last_name": "Destek",
        "username": "KeyVadiDestek",
        "photo_path": r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\keyvadi_chat_logo_1783808152574.png",
    },
    {
        "phone": "+13412648927",
        "session": "1AZWarzsBuyAiCinDXh9__cCrDW0v3_s7zFaKzpygVSlkMgV3QEKHAtoRcb9zWetfi-F3Wsbb6lF8yCMsPPEdKDGI9q-Ojf5HmK-GZVlrDpl65za7Ryou5Vx7L9jyX8jiwBpJ8LDkH4qg2l5pT-IQQqtPfFyaPwGfp-kIgzpHCvI0YzQy27Gk0xDsz8syrSulTiZ8dFsJW8sxI4pHUOerilaOFmv6ChOee7ZBBdXN_bm75f0Tg__UwxXOz0NSTWqYyqTiodBeHvFVVGq5eQAwZCUDTcQsTktRhzxrBQ3pP6twIpeTSQKtuuJ_YvJ5WVQ_No3b27TOFajGHuNu_9MZBSh2qxN13ls=",
        "brand": "LisansArena",
        "first_name": "LisansArena",
        "last_name": "Destek",
        "username": "LisansArenaDestek",
        "photo_path": r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\adobe_cc_lisansarena_1783811656872.png",
    },
]

async def setup_account(acc):
    phone = acc["phone"]
    print(f"\n[{phone} - {acc['brand']}] Baglaniyor...")
    client = TelegramClient(StringSession(acc["session"]), api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        print(f"[{phone}] YETKISIZ! Atlanıyor.")
        await client.disconnect()
        return

    # 1. Profile name
    print(f"[{phone}] İsim ayarlanıyor: {acc['first_name']} {acc['last_name']}")
    await client(UpdateProfileRequest(
        first_name=acc["first_name"],
        last_name=acc["last_name"],
        about=""
    ))
    print(f"[{phone}] [OK] İsim ayarlandi.")

    # 2. Username
    print(f"[{phone}] Username ayarlanıyor: @{acc['username']}")
    try:
        await client(UpdateUsernameRequest(username=acc["username"]))
        print(f"[{phone}] [OK] Username ayarlandi.")
    except Exception as e:
        print(f"[{phone}] Username hatasi (zaten alinmis olabilir): {e}")

    # 3. Privacy settings - phone hidden from everyone
    print(f"[{phone}] Gizlilik ayarları yapılıyor...")
    try:
        # Phone number: nobody
        await client(UpdatePrivacyRequest(
            key=InputPrivacyKeyPhoneNumber(),
            rules=[InputPrivacyValueDisallowAll()]
        ))
        print(f"[{phone}] [OK] Telefon numarasi gizlendi.")
    except Exception as e:
        print(f"[{phone}] Telefon gizlilik hatasi: {e}")

    try:
        # Last seen: nobody
        await client(UpdatePrivacyRequest(
            key=InputPrivacyKeyStatusTimestamp(),
            rules=[InputPrivacyValueDisallowAll()]
        ))
        print(f"[{phone}] [OK] Son gorulme gizlendi.")
    except Exception as e:
        print(f"[{phone}] Son gorulme hatasi: {e}")

    try:
        # Profile photo: contacts only
        await client(UpdatePrivacyRequest(
            key=InputPrivacyKeyProfilePhoto(),
            rules=[InputPrivacyValueAllowAll()]
        ))
        print(f"[{phone}] [OK] Profil fotografi herkese acik.")
    except Exception as e:
        print(f"[{phone}] Profil foto gizlilik hatasi: {e}")

    try:
        # Calls: nobody
        await client(UpdatePrivacyRequest(
            key=InputPrivacyKeyPhoneCall(),
            rules=[InputPrivacyValueDisallowAll()]
        ))
        print(f"[{phone}] [OK] Aramalari kapatti.")
    except Exception as e:
        print(f"[{phone}] Arama gizlilik hatasi: {e}")

    try:
        # Forwards: nobody
        await client(UpdatePrivacyRequest(
            key=InputPrivacyKeyForwards(),
            rules=[InputPrivacyValueDisallowAll()]
        ))
        print(f"[{phone}] [OK] Iletme gizligi kapatti.")
    except Exception as e:
        print(f"[{phone}] Iletme gizlilik hatasi: {e}")

    # 4. Profile photo
    if acc.get("photo_path") and os.path.exists(acc["photo_path"]):
        print(f"[{phone}] Profil fotografi yukleniyor...")
        try:
            uploaded = await client.upload_file(acc["photo_path"])
            await client(UploadProfilePhotoRequest(file=uploaded))
            print(f"[{phone}] [OK] Profil fotografi yuklendi.")
        except Exception as e:
            print(f"[{phone}] Profil foto hatasi: {e}")
    else:
        print(f"[{phone}] Profil foto dosyasi bulunamadi, atlanıyor.")

    print(f"[{phone}] [{acc['brand']}] Kurulum tamamlandi!")
    await client.disconnect()

async def main():
    print("=" * 60)
    print("YENİ HESAP KURULUMU (İSİM + USERNAME + GİZLİLİK + FOTO)")
    print("=" * 60)
    for acc in accounts:
        await setup_account(acc)
        print("-" * 60)

if __name__ == "__main__":
    asyncio.run(main())
