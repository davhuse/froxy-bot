import asyncio
import urllib.request
import json
import ssl
import sys
import os
from datetime import datetime, timedelta, timezone

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import DeletePhotosRequest, GetUserPhotosRequest
from telethon.tl.types import InputPhoto

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get_render_config():
    req = urllib.request.Request('https://veridia-bot.onrender.com/api/config')
    with urllib.request.urlopen(req, context=ctx) as r:
        return json.loads(r.read().decode('utf-8'))

def save_render_config(cfg):
    data = json.dumps(cfg).encode('utf-8')
    req = urllib.request.Request(
        'https://veridia-bot.onrender.com/api/config',
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, context=ctx) as r:
        return json.loads(r.read().decode('utf-8'))

async def reset_profile(client, account_name):
    """Reset profile: clear bio, name, username, remove photos"""
    print(f"\n{'='*50}")
    print(f"[{account_name}] Profil sıfırlanıyor...")
    
    me = await client.get_me()
    print(f"  Mevcut: {me.first_name} {me.last_name or ''} | @{me.username or 'yok'} | ID: {me.id}")
    
    # 1. Clear bio and name
    try:
        await client(UpdateProfileRequest(
            first_name='User',
            last_name='',
            about=''
        ))
        print(f"  ✅ İsim 'User' olarak değiştirildi, bio temizlendi")
    except Exception as e:
        print(f"  ⚠️ Profil güncelleme hatası: {e}")
    
    # 2. Remove username
    try:
        if me.username:
            await client(UpdateUsernameRequest(username=''))
            print(f"  ✅ Kullanıcı adı (@{me.username}) kaldırıldı")
        else:
            print(f"  ℹ️ Zaten kullanıcı adı yok")
    except Exception as e:
        print(f"  ⚠️ Kullanıcı adı kaldırma hatası: {e}")
    
    # 3. Remove profile photos
    try:
        photos = await client(GetUserPhotosRequest(
            user_id='me',
            offset=0,
            max_id=0,
            limit=100
        ))
        if photos.photos:
            input_photos = [
                InputPhoto(
                    id=p.id,
                    access_hash=p.access_hash,
                    file_reference=p.file_reference
                ) for p in photos.photos
            ]
            await client(DeletePhotosRequest(id=input_photos))
            print(f"  ✅ {len(photos.photos)} profil fotoğrafı silindi")
        else:
            print(f"  ℹ️ Profil fotoğrafı yok")
    except Exception as e:
        print(f"  ⚠️ Fotoğraf silme hatası: {e}")

async def delete_recent_messages(client, account_name):
    """Delete all messages sent by this account in the last 24 hours from groups"""
    print(f"\n[{account_name}] Son 24 saatteki mesajlar siliniyor...")
    
    me = await client.get_me()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    
    total_deleted = 0
    groups_checked = 0
    
    async for dialog in client.iter_dialogs():
        # Only process groups and channels (not private chats)
        if not dialog.is_group and not dialog.is_channel:
            continue
        
        groups_checked += 1
        group_name = dialog.name or str(dialog.id)
        deleted_in_group = 0
        
        try:
            msg_ids_to_delete = []
            async for msg in client.iter_messages(dialog.id, from_user='me', offset_date=None):
                if msg.date and msg.date < cutoff:
                    break  # Messages older than 24 hours, stop
                msg_ids_to_delete.append(msg.id)
            
            if msg_ids_to_delete:
                # Delete in batches of 100
                for i in range(0, len(msg_ids_to_delete), 100):
                    batch = msg_ids_to_delete[i:i+100]
                    await client.delete_messages(dialog.id, batch)
                    deleted_in_group += len(batch)
                    await asyncio.sleep(0.5)
                
                print(f"  🗑️ @{group_name}: {deleted_in_group} mesaj silindi")
                total_deleted += deleted_in_group
        except Exception as e:
            err_name = type(e).__name__
            if 'Forbidden' in err_name or 'forbidden' in str(e).lower():
                pass  # Can't delete in this group, skip silently
            else:
                print(f"  ⚠️ @{group_name}: {err_name}")
        
        await asyncio.sleep(0.3)
    
    print(f"  📊 Toplam: {groups_checked} grup kontrol edildi, {total_deleted} mesaj silindi")

async def main():
    print("🔧 Hesap Sıfırlama ve Temizleme Scripti")
    print("=" * 50)
    
    # Get config from Render
    print("\n📥 Render'dan config alınıyor...")
    cfg = get_render_config()
    
    session2 = cfg.get("ad_string_session2", "")
    session3 = cfg.get("ad_string_session3", "")
    
    accounts = []
    if session2:
        accounts.append(("Hesap #2 (KeyVadi)", session2, "ad_string_session2"))
    if session3:
        accounts.append(("Hesap #3 (LisansArena)", session3, "ad_string_session3"))
    
    if not accounts:
        print("❌ Aktif hesap bulunamadı!")
        return
    
    print(f"✅ {len(accounts)} hesap bulundu")
    
    # Process each account
    for account_name, session_str, config_key in accounts:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                print(f"\n❌ {account_name} yetkilendirilmemiş, atlanıyor...")
                continue
            
            # Step 1: Delete recent messages first (before losing access)
            await delete_recent_messages(client, account_name)
            
            # Step 2: Reset profile
            await reset_profile(client, account_name)
            
            await client.disconnect()
            print(f"\n✅ [{account_name}] Tamamlandı!")
            
        except Exception as e:
            print(f"\n❌ [{account_name}] Hata: {e}")
    
    # Step 3: Stop the ad bot on Render first
    print("\n\n🛑 Reklam botu durduruluyor...")
    try:
        stop_req = urllib.request.Request(
            'https://veridia-bot.onrender.com/api/stop',
            data=b'{}',
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(stop_req, context=ctx) as r:
            result = json.loads(r.read().decode('utf-8'))
            print(f"  Sonuç: {result}")
    except Exception as e:
        print(f"  ⚠️ Bot durdurma hatası: {e}")
    
    # Step 4: Remove session strings from config
    print("\n🔑 Session string'ler config'den kaldırılıyor...")
    cfg = get_render_config()  # Re-fetch fresh config
    
    cfg["ad_string_session2"] = ""
    cfg["ad_string_session3"] = ""
    cfg["ad_string_session_2"] = ""
    cfg["ad_string_session_3"] = ""
    
    result = save_render_config(cfg)
    print(f"  Config güncelleme sonucu: {result}")
    
    print("\n" + "=" * 50)
    print("✅ TÜM İŞLEMLER TAMAMLANDI!")
    print("=" * 50)
    print("\nÖzet:")
    print("  • Profiller sıfırlandı (isim, bio, username, fotoğraf)")
    print("  • Son 24 saatteki grup mesajları silindi")
    print("  • Session string'ler Render config'den kaldırıldı")
    print("  • Reklam botu durduruldu")
    print("\n📌 Şimdi hesapları kendin ayarlayabilirsin!")

if __name__ == "__main__":
    asyncio.run(main())
