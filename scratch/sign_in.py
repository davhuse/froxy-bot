import asyncio
import sys
import json
import urllib.request
import ssl
from telethon import TelegramClient
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

async def main():
    code = sys.argv[1]
    pwd = sys.argv[2] if len(sys.argv) > 2 else None
    name = sys.argv[3] if len(sys.argv) > 3 else "Destek"
    config_key = sys.argv[4] if len(sys.argv) > 4 else None
    
    with open('pending_login.json', 'r') as f:
        data = json.load(f)
        
    phone = data['phone']
    phone_code_hash = data['phone_code_hash']
    session_string = data['session_string']
    
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    print(f"Signing in {phone} with code {code}...")
    try:
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        print("✅ Signed in successfully!")
    except Exception as e:
        if 'SessionPasswordNeededError' in str(type(e)):
            print("⚠️ 2FA Password needed!")
            if pwd:
                await client.sign_in(password=pwd)
                print("✅ Signed in successfully with password!")
            else:
                print("❌ Need password but none provided.")
                return
        else:
            print(f"❌ Failed to sign in: {e}")
            return
            
    # Disable 2FA
    try:
        pwd_request = await client(GetPasswordRequest())
        if pwd_request.has_password:
            await client.edit_2fa(current_password=pwd, new_password=None)
            print("✅ 2FA disabled.")
    except Exception as e:
        print(f"⚠️ Could not disable 2FA: {e}")
        
    try:
        await client(UpdateProfileRequest(first_name=name, last_name='', about='Lisans ve Abonelik Servisleri'))
        print(f"✅ Profile updated to {name}")
    except Exception as e:
        print(f"⚠️ Error updating profile: {e}")
        
    new_session_string = client.session.save()
    if config_key:
        cfg = get_render_config()
        cfg[config_key] = new_session_string
        save_render_config(cfg)
        print(f"✅ Saved to Render config as {config_key}")
        
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
