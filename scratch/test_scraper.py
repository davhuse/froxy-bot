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

# Negative keywords from otomatik_katil.py
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

async def main():
    client = TelegramClient(StringSession(session1), api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("Not authorized")
            return
            
        print("Running scraper search for a few test keywords...")
        keywords = ["yapay zeka", "smm panel", "dijital ilan"]
        
        for kw in keywords:
            print(f"\nSearching for keyword: '{kw}'")
            res = await client(SearchRequest(q=kw, limit=20))
            for chat in res.chats:
                is_group = False
                if isinstance(chat, Channel):
                    if not getattr(chat, 'broadcast', False):
                        is_group = True
                elif isinstance(chat, Chat):
                    is_group = True
                    
                if not is_group or not chat.username:
                    continue
                    
                username = chat.username
                title = chat.title
                member_count = getattr(chat, 'participants_count', None)
                join_request = getattr(chat, 'join_request', False)
                
                # Check negative keywords and sales keywords
                title_lower = title.lower()
                has_sales_word = any(w in title_lower for w in sales_keywords)
                has_negative = any(w in title_lower for w in NEGATIVE_KEYWORDS)
                
                status = "PASS"
                reasons = []
                if member_count is not None and member_count < 500:
                    status = "SKIP"
                    reasons.append(f"low_members ({member_count})")
                if has_negative:
                    status = "SKIP"
                    reasons.append("negative_keyword")
                if not has_sales_word:
                    status = "SKIP"
                    reasons.append("no_sales_word")
                if join_request:
                    status = "SKIP"
                    reasons.append("join_request_required")
                    
                print(f"  @{username} | Members: {member_count} | Join Request: {join_request} | Status: {status} | Reasons: {reasons}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
