import asyncio
import sys
import os
import json
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel, Chat

sys.stdout.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
session1 = "1BJWap1sBu5KV1uEObjEZe-rlVuuHYuo-O2bLBaFvRYV4spqDLhyEURnGdwerOqZxDOVAeU9RhC0fYp9CfA5VSeZj4gEBaeQPUFcSZ9FAuekK1BuiV-dw0j3Ip88GM88f5LJiEV92z3uYKx6KbevaJhb_tWgLscE71fH1yFnKiCczMd1qNpeznDoan-L2eR9PISWMYjbiPgUDurr5mNChB0CTwzhdzx3DiSqzdNlJAwK8ciB0cfNOOc0cncb2r-pBjSpu4PK42Rczv5M6kuAUjQV6orOs8GSuctQ3yOF4vqTGeT9XXB7yQfFetro0sQjRghitSg6ZY5qOQ2IzSMffZWMjAuuYflg="

# Target keywords for scraping
SCRAPE_KEYWORDS = [
    "kupon satış", "kod satış", "kupon çek", "kupon satis",
    "alım satım", "ticaret grubu", "satış grubu", "ilan grubu",
    "hesap satış", "dijital ilan", "smm panel",
    "indirim kupon", "fırsat indirim", "reklam grubu",
    "alim satim", "e-ticaret satış", "dijital satış",
    "referans reklam", "epin satış", "program satış",
    "yazılım ticaret", "dijital lisans", "reklam pazar",
    "reklam referans", "dijital pazar", "sosyal medya bayilik",
    "yapay zeka", "chatgpt türkçe", "ai araçları", "ai tools",
    "adobe lisans", "canva pro", "premium hesap",
    "lisans satış", "yazılım indirim",
    "trendyol indirim", "trendyol kupon", "yemek kuponu",
    "indirim kodu", "promosyon kodu", "kampanya kodu",
    "dijital pazarlama", "sosyal medya yönetimi",
    "pazar yeri"
]

NEGATIVE_KEYWORDS = [
    "sigara", "vape", "puff", "tütün", "likit", "shisha", "nargile", "elektronik sigara", "elektroniksigara",
    "ayakkabı", "ayakkabi", "giyim", "butik", "moda", "elbise", "çanta", "canta",
    "brawl", "pubg", "valorant", "clash", "roblox", "free fire", "mobile legends", "metin2", "knight online",
    "korg", "pa800", "pa2x", "pa600", "pa900", "orgcu", "müzik", "muzik", "enstrüman",
    "gürcistan", "gurcistan", "batum", "tiflisi",
    "escort", "sex", "porno", "ifşa", "ifsa", "adult", "travesti",
    "film", "dizi", "izle", "sinema", "warez",
    "bahis", "iddaa", "casino", "kumar", "rulet", "bet", "kazan", "tahmin",
    "araba", "oto", "motor", "vasıta", "toptan", "tekstil", "diş", "hekim", "medikal", 
    "kitap", "ders", "gayrimenkul", "emlak", "ev", "daire", "kiralık", "arazi", "arsa",
    "telefon", "cihaz", "parça", "donanım", "pc"
]

sales_keywords = [
    "satış", "satis", "ticaret", "ilan", "reklam", "kupon", "indirim",
    "shopier", "hesap", "alım", "satım", "alim", "satim", "smm", "kod",
    "ucuz", "ref", "pazar", "lisans", "premium", "dijital", "adobe", "canva",
    "trendyol", "kampanya", "fırsat", "firsat", "epin", "yazılım", "yazilim", 
    "yapay zeka", "ai", "chatgpt"
]

gruplar_static = [
    "ilanticaret", "Nightsatis", "alimsatimmerkezii", "kuponceking",
    "-1001572316417", "kuponsatimalim", "indirimkodusatis", "ticaretsaha",
    "ticaretforumofficial", "ticaretguvenilir", "kuponsatisgrup",
    "kuponhesapsatis", "kuponsatislari0", "TsmTicaret", "reklamreferans",
    "sosyalmedyaalimsatimticaret", "YuceKuponSatis"
]

def get_list(dosya):
    if os.path.exists(dosya):
        with open(dosya, 'r', encoding='utf-8') as f:
            return set(line.strip().lower() for line in f if line.strip())
    return set()

async def main():
    client = TelegramClient(StringSession(session1), api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("Not authorized")
            return
            
        # Get currently joined group usernames
        joined_usernames = set()
        print("Gathering joined dialogs...")
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                username = getattr(dialog.entity, 'username', None)
                if username:
                    joined_usernames.add(username.lower())
        print(f"Already joined in {len(joined_usernames)} groups.")
        
        # Load blacklist
        blacklist_lower = get_list("blacklist.txt")
        print(f"Blacklist size: {len(blacklist_lower)}")
        
        # Exclude static target list
        static_lower = set(x.lower() for x in gruplar_static)
        
        discovered_groups = []
        checked = set()
        
        print("\nStarting search across all keywords...")
        for kw in SCRAPE_KEYWORDS:
            print(f"Searching: '{kw}'")
            try:
                res = await client(SearchRequest(q=kw, limit=50))
                for chat in res.chats:
                    username = getattr(chat, 'username', None)
                    if not username or username.lower() in checked:
                        continue
                    username_lower = username.lower()
                    checked.add(username_lower)
                    
                    # Exclude already joined, static list, and blacklist
                    if username_lower in joined_usernames:
                        continue
                    if username_lower in static_lower:
                        continue
                    if username_lower in blacklist_lower:
                        continue
                        
                    is_group = False
                    if isinstance(chat, Channel):
                        if not getattr(chat, 'broadcast', False):
                            is_group = True
                    elif isinstance(chat, Chat):
                        is_group = True
                        
                    if not is_group:
                        continue
                        
                    # Filter: Member count >= 500
                    member_count = getattr(chat, 'participants_count', None)
                    if member_count is not None and member_count < 500:
                        continue
                        
                    # Filter: join_request (Approval-required) must be False
                    join_request = getattr(chat, 'join_request', False)
                    if join_request:
                        continue
                        
                    # Filter: Title keywords
                    title = getattr(chat, 'title', '') or ""
                    title_lower = title.lower()
                    has_sales_word = any(w in title_lower for w in sales_keywords)
                    has_negative = any(w in title_lower for w in NEGATIVE_KEYWORDS)
                    
                    if has_negative or not has_sales_word:
                        continue
                        
                    # This is a valid, high-quality, instant-join group!
                    discovered_groups.append((username, title, member_count))
                    print(f"  ✨ Found: @{username} | Title: '{title}' | Members: {member_count}")
                    
                await asyncio.sleep(2)
            except Exception as kw_e:
                print(f"  Error searching '{kw}': {kw_e}")
                
        print(f"\nSearch complete! Found {len(discovered_groups)} groups.")
        
        # Write to scraped_groups.txt and auto_groups.txt
        if discovered_groups:
            # We will append the discovered groups to scraped_groups.txt
            with open("scraped_groups.txt", "w", encoding="utf-8") as f:
                for username, title, mc in discovered_groups:
                    f.write(username + "\n")
            print("Wrote to scraped_groups.txt successfully.")
            
            # Write to auto_groups.txt so that the bot will include them in targeting
            with open("auto_groups.txt", "w", encoding="utf-8") as f:
                for username, title, mc in discovered_groups:
                    f.write(username + "\n")
            print("Wrote to auto_groups.txt successfully.")
            
            # Sync to Firestore (sadece auto_groups_list'i güncelliyoruz)
            try:
                import requests
                PROJECT_ID = "bot-2-63772"
                API_KEY = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
                url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/reklam/state?updateMask.fieldPaths=auto_groups_list&key={API_KEY}"
                
                auto_groups_content = "\n".join([g[0] for g in discovered_groups]) + "\n"
                
                fields = {
                    "auto_groups_list": {"stringValue": auto_groups_content}
                }
                requests.patch(url, json={"fields": fields}, timeout=10)
                print("Successfully synced discovered groups to Firestore auto_groups_list!")
            except Exception as fs_err:
                print(f"Firestore sync error: {fs_err}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
