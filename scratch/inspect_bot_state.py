import asyncio
import json
import os
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import (
    FloodWaitError, UsernameNotOccupiedError, UsernameInvalidError, 
    ChannelPrivateError, UserBannedInChannelError
)

sys.stdout.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

# Load targets from otomatik_katil.py
gruplar = [
    "ticaretforumofficial",
    "sultanbeyliikinciel0",
    "tahaaslan11",
    "casinox_grup",
    "ReklamOnliene",
    "alimsatimmerkezii",
    "illegalalimsatimerkezi",
    "ilanticaret",
    "reklamreferans",
    "sosyalmedyaalimsatimticaret",
    "ReferansReklamYardimlasma",
    "sanalalimsatimticaret",
    "kuponsatisgrup",
    "referansreklam1",
    "referanslinkpaylasimigrup",
    "kuponsatislari0",
    "YuceKuponSatis",
    "letgoilanlari",
    "-1001572316417",
    "-3608209943",
    "ticar4t",
    "kuponhesapsatis",
    "reklamvereferanss",
    "kuponvekodsatisgrubu",
    "indirimkodusatis",
]

def get_all_protected_groups():
    protected = set(g.lower() for g in gruplar)
    if os.path.exists("auto_groups.txt"):
        try:
            with open("auto_groups.txt", "r", encoding="utf-8") as f:
                for line in f:
                    g = line.strip().lower()
                    if g:
                        protected.add(g)
        except:
            pass
    return protected

async def inspect_client(session_str, name):
    print(f"\n======================================")
    print(f"Inspecting Client: {name}")
    print(f"======================================")
    
    if not session_str:
        print("No session string configured.")
        return
        
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("Client is not authorized!")
            return
            
        me = await client.get_me()
        print(f"Authorized as: @{me.username} ({me.first_name} {me.last_name or ''}) ID: {me.id}")
        
        # Get dialogs
        print("Fetching dialogs...")
        dialogs = {}
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                username_lower = dialog.entity.username.lower() if (hasattr(dialog.entity, 'username') and dialog.entity.username) else None
                dialog_id_str = str(dialog.id)
                if username_lower:
                    dialogs[username_lower] = dialog.entity
                dialogs[dialog_id_str] = dialog.entity
                
        targets = get_all_protected_groups()
        print(f"Total targets: {len(targets)}")
        
        joined = []
        not_joined = []
        blacklisted = []
        
        # Load blacklist
        blacklist = set()
        if os.path.exists("blacklist.txt"):
            try:
                with open("blacklist.txt", "r", encoding="utf-8") as f:
                    blacklist = set(l.strip().lower() for l in f if l.strip())
            except:
                pass
                
        for t in sorted(list(targets)):
            t_lower = t.lower()
            if t_lower in blacklist:
                blacklisted.append(t)
            elif t_lower in dialogs:
                joined.append(t)
            else:
                not_joined.append(t)
                
        print(f"\nJoined ({len(joined)}):")
        for g in joined:
            entity = dialogs[g]
            title = getattr(entity, 'title', '')
            print(f" - @{g} (Title: {title})")
            
        print(f"\nBlacklisted ({len(blacklisted)}):")
        for g in blacklisted:
            print(f" - @{g}")
            
        print(f"\nNot Joined ({len(not_joined)}):")
        for g in not_joined:
            # Check what happens if we get entity
            try:
                entity = await client.get_entity(g)
                print(f" - @{g}: Not in dialogs but we can resolve it! (Title: {getattr(entity, 'title', '')})")
            except Exception as e:
                print(f" - @{g}: Cannot resolve: {type(e).__name__} - {e}")
                
    except Exception as e:
        print(f"Client inspection error: {e}")
    finally:
        await client.disconnect()

async def main():
    if not os.path.exists("bot_config.json"):
        print("bot_config.json not found!")
        return
        
    with open("bot_config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
        
    session1 = cfg.get("ad_string_session", "")
    session2 = cfg.get("ad_string_session_2", "")
    
    await inspect_client(session1, "Hesap #1")
    await inspect_client(session2, "Hesap #2")

if __name__ == '__main__':
    asyncio.run(main())
