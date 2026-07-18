import asyncio
import re
import urllib.request
import ssl
import sys
import os
import json
import time
from bs4 import BeautifulSoup
from telethon import TelegramClient
import telethon.errors
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.account import GetPasswordRequest

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

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

def get_code_and_password(url):
    for i in range(12):  # poll for 1 minute
        time.sleep(5)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, context=ctx) as r:
                html = r.read().decode('utf-8')
                soup = BeautifulSoup(html, 'html.parser')
                text = soup.get_text()
                
                if "无三十分钟内的登录消息" in text or "没有消息" in text:
                    print("  Waiting for code...")
                    continue
                
                print(f"  Page content extracted:\n{text.strip()}")
                
                # Parse code
                code_match = re.search(r'\b(\d{5})\b', text)
                code = code_match.group(1) if code_match else None
                
                # Try to extract password. Pattern matches Chinese/English labels
                pwd_match = re.search(r'(?:密码|Password|Şifre|two-step)[^\w]*([A-Za-z0-9@#$%^&+=_!]+)', text, re.IGNORECASE)
                password = pwd_match.group(1) if pwd_match else None
                
                # If code is found, wait a moment just to be sure we got full text, but actually just return
                if code:
                    return code, password
        except Exception as e:
            print(f"  Error fetching code: {e}")
    return None, None

async def login_account(phone, url, name, username=None):
    print(f"\n[{name}] Logging in {phone}...")
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    
    print("  Sending code request...")
    try:
        hash_obj = await client.send_code_request(phone)
        phone_code_hash = hash_obj.phone_code_hash
    except telethon.errors.FloodWaitError as e:
        print(f"  ❌ Flood wait for {e.seconds} seconds.")
        await client.disconnect()
        return None
    except Exception as e:
        print(f"  ❌ Error requesting code: {e}")
        await client.disconnect()
        return None
    
    print("  Waiting for code from URL...")
    code, pwd = get_code_and_password(url)
    
    if not code:
        print("  ❌ Failed to get code from webpage.")
        await client.disconnect()
        return None
        
    print(f"  Received code: {code}")
    if pwd:
        print(f"  Received password: {pwd}")
        
    try:
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        print("  ✅ Signed in successfully without password!")
    except telethon.errors.SessionPasswordNeededError:
        print("  ⚠️ 2FA Password needed!")
        if pwd:
            try:
                await client.sign_in(password=pwd)
                print("  ✅ Signed in successfully with password!")
            except telethon.errors.PasswordHashInvalidError:
                print("  ❌ Incorrect 2FA password!")
                await client.disconnect()
                return None
        else:
            print("  ❌ 2FA required but no password found on page!")
            await client.disconnect()
            return None
    except telethon.errors.PhoneCodeInvalidError:
        print("  ❌ Invalid phone code!")
        await client.disconnect()
        return None
    except telethon.errors.PhoneCodeExpiredError:
        print("  ❌ Phone code expired!")
        await client.disconnect()
        return None
    
    # Disable 2FA
    try:
        pwd_request = await client(GetPasswordRequest())
        if pwd_request.has_password:
            print("  Disabling 2FA password...")
            await client.edit_2fa(current_password=pwd, new_password=None)
            print("  ✅ 2FA disabled.")
        else:
            print("  ℹ️ 2FA is already disabled.")
    except Exception as e:
        print(f"  ⚠️ Could not disable 2FA: {e}")
        
    # Update profile
    print("  Updating profile...")
    try:
        await client(UpdateProfileRequest(
            first_name=name,
            last_name='',
            about='Lisans ve Abonelik Servisleri'
        ))
        print(f"  ✅ Profile updated to {name}")
    except Exception as e:
        print(f"  ⚠️ Error updating profile: {e}")
        
    if username:
        try:
            await client(UpdateUsernameRequest(username=username))
            print(f"  ✅ Username updated to {username}")
        except Exception as e:
            print(f"  ⚠️ Error updating username: {e}")
            
    session_string = client.session.save()
    await client.disconnect()
    return session_string

async def main():
    acc1 = {
        'phone': '+13869914668',
        'url': 'https://jiema.didiapi.uk/getcode?id=f505373d-5219-4a60-bcea-96f473fe72f4',
        'name': 'KeyVadi',
        'config_key': 'ad_string_session2'
    }
    
    acc2 = {
        'phone': '+14176608361',
        'url': 'https://jiema.didiapi.uk/getcode?id=0563f083-9630-4def-ba77-3e335563efe9',
        'name': 'LisansArena',
        'config_key': 'ad_string_session3'
    }
    
    cfg = get_render_config()
    
    for acc in [acc1, acc2]:
        session_str = await login_account(acc['phone'], acc['url'], acc['name'])
        if session_str:
            cfg[acc['config_key']] = session_str
            print(f"  ✅ Saved session for {acc['name']}")
            
    print("\nSaving config to Render...")
    save_render_config(cfg)
    print("✅ Done!")

if __name__ == '__main__':
    asyncio.run(main())
