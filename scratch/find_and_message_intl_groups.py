import os
import json
import asyncio
import re
import sys
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'
CONFIG_FILE = "bot_config.json"

AD_TEXT = (
    "🤖 **Get Premium AI & Design Accounts Instantly!** 🎨\n"
    "━━━━━━━━━━━━━━━━━\n"
    "Looking for cheap, instant-delivery premium packages? We support international cards!\n\n"
    "🔥 **AI Packages (ChatGPT, Claude, Gemini, DeepSeek & 400+ models):**\n"
    "• Starter Package (5K Credits) -> **$3.99**\n"
    "• Popular Package (15K Credits) -> **$7.99** (Includes Image Generation)\n"
    "• Professional Package (50K Credits) -> **$13.99**\n\n"
    "🎨 **Design & License Accounts:**\n"
    "• Canva Pro, Adobe CC, CapCut Pro, Duolingo Premium and more at cheapest rates!\n\n"
    "💳 **Secure Shopier Payment (Visa, Mastercard, Amex supported worldwide)**\n"
    "🤖 **Order via Telegram Bots:**\n"
    "• AI Packages: @FroxyDestekBOT\n"
    "• Premium Accounts: @KeyVadiSatisBot\n"
    "━━━━━━━━━━━━━━━━━"
)

async def main():
    print("🚀 Connecting to Habil's Telegram account...")
    
    # Load config
    string_session_key = ""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                string_session_key = cfg.get("ad_string_session", "")
        except Exception as e:
            print(f"Error loading config: {e}")
            
    if not string_session_key:
        print("❌ Error: ad_string_session not found in bot_config.json")
        return
        
    client = TelegramClient(StringSession(string_session_key), API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ Error: Client is not authorized!")
        return
        
    me = await client.get_me()
    print(f"✅ Logged in as: {me.first_name} (ID: {me.id})")
    
    # 77 keywords or search keywords in English
    keywords = [
        "chatgpt english", "chatgpt chat", "ai chat english",
        "smm chat", "smm promotion", "seo chat", "marketing group",
        "freelance english", "graphic design chat", "design resources chat",
        "game trade", "steam keys buy", "premium account chat", "promotion group",
        "advertisement english", "crypto promotion chat", "advertising chat"
    ]
    
    target_groups = []
    seen_usernames = set()
    
    print("🔍 Searching for international English groups (>1000 members)...")
    
    for kw in keywords:
        if len(target_groups) >= 5:
            break
        print(f"🔎 Searching for: '{kw}'")
        try:
            result = await client(SearchRequest(q=kw, limit=50))
            for chat in result.chats:
                if len(target_groups) >= 5:
                    break
                    
                # Must be a group/supergroup
                is_group = False
                if isinstance(chat, types.Channel):
                    if not getattr(chat, 'broadcast', False):
                        is_group = True
                elif isinstance(chat, types.Chat):
                    is_group = True
                    
                username = getattr(chat, 'username', None)
                if not is_group or not username:
                    continue
                    
                username_lower = username.lower()
                if username_lower in seen_usernames:
                    continue
                seen_usernames.add(username_lower)
                
                # Check member count (>1000)
                member_count = getattr(chat, 'participants_count', None)
                if member_count is None or member_count < 1000:
                    continue
                    
                # Add to targets
                target_groups.append(chat)
                print(f"  ✨ Found: @{username} | Members: {member_count} | Title: '{chat.title}'")
                
        except Exception as e:
            print(f"  ⚠️ Error searching '{kw}': {e}")
            
    print(f"\n📢 Found {len(target_groups)} target groups. Joining and posting ad...")
    
    success_count = 0
    for chat in target_groups:
        username = chat.username
        print(f"👥 Processing group: @{username}...")
        try:
            # Join the group/channel
            await client(JoinChannelRequest(chat))
            print(f"  ✅ Joined @{username}")
            
            # Wait 5 seconds before posting
            await asyncio.sleep(5)
            
            # Send message
            await client.send_message(chat, AD_TEXT)
            print(f"  ✉️ Successfully sent ad to @{username}!")
            success_count += 1
            
            # Cooldown sleep
            await asyncio.sleep(10)
        except FloodWaitError as e:
            print(f"  ⏳ FloodWait: Must sleep for {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"  ❌ Error processing @{username}: {e}")
            
    print(f"\n🎉 Finished outreach! Posted to {success_count} groups out of {len(target_groups)} found.")

if __name__ == "__main__":
    asyncio.run(main())
