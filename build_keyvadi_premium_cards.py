# -*- coding: utf-8 -*-
import json
import os

CARD_MAPPING = [
    ("youtube", "assets/products/card_clean_youtube.jpg"),
    ("canva", "assets/products/card_clean_canva.jpg"),
    ("netflix", "assets/products/card_clean_netflix.jpg"),
    ("chatgpt", "assets/products/card_clean_chatgpt.jpg"),
    ("gpt", "assets/products/card_clean_chatgpt.jpg"),
    ("gemini", "assets/products/card_clean_gemini.jpg"),
    ("spotify", "assets/products/card_clean_spotify.jpg"),
    ("fc 26", "assets/products/card_clean_fc26.jpg"),
    ("fc26", "assets/products/card_clean_fc26.jpg"),
    ("steam", "assets/products/card_clean_steam.jpg"),
    ("capcut", "assets/products/card_clean_capcut.jpg"),
    ("xbox", "assets/products/card_clean_xbox.jpg"),
    ("game pass", "assets/products/card_clean_xbox.jpg"),
    ("gamepass", "assets/products/card_clean_xbox.jpg"),
    ("duolingo", "assets/products/card_clean_duolingo.jpg"),
    ("discord", "assets/products/card_clean_discord.jpg"),
    ("nitro", "assets/products/card_clean_discord.jpg"),
    ("kaspersky", "assets/products/card_clean_kaspersky.jpg"),
    ("windows", "assets/products/card_clean_windows.jpg"),
    ("win 11", "assets/products/card_clean_windows.jpg"),
    ("win 10", "assets/products/card_clean_windows.jpg"),
    ("office", "assets/products/card_clean_office.jpg"),
    ("365", "assets/products/card_clean_office.jpg"),
    ("exxen", "assets/products/card_clean_exxen.jpg"),
    ("prime", "assets/products/card_clean_prime.jpg"),
    ("hbo", "assets/products/card_clean_hbo.jpg"),
    ("roblox", "assets/products/card_clean_roblox.jpg"),
    ("minecraft", "assets/products/card_clean_minecraft.jpg"),
    ("cape", "assets/products/card_clean_minecraft.jpg"),
    ("envato", "assets/products/card_clean_envato.jpg"),
    ("freepik", "assets/products/card_clean_freepik.jpg"),
    ("adobe", "assets/products/card_clean_adobe.jpg"),
    ("creative", "assets/products/card_clean_adobe.jpg"),
    ("photoshop", "assets/products/card_clean_adobe.jpg"),
    ("zula", "assets/products/card_clean_zula.jpg"),
    ("grammarly", "assets/products/card_clean_grammarly.jpg"),
    ("deepl", "assets/products/card_clean_deepl.jpg"),
    ("gamma", "assets/products/card_clean_gamma.jpg"),
    ("magnific", "assets/products/card_clean_magnific.jpg"),
    ("perplexity", "assets/products/card_clean_perplexity.jpg"),
    ("grok", "assets/products/card_clean_grok.jpg"),
    ("scribd", "assets/products/card_clean_scribd.jpg"),
    ("shell", "assets/products/card_clean_shell.jpg"),
    ("telegram", "assets/products/card_clean_telegram.jpg"),
    ("crunchyroll", "assets/products/card_clean_crunchyroll.jpg"),
    ("gmail", "assets/products/card_clean_gmail.jpg"),
    ("instagram", "assets/products/card_clean_instagram.jpg")
]

def resolve_card(title):
    t = title.lower()
    for kw, card in CARD_MAPPING:
        if kw in t:
            return card
    return "assets/products/card_clean_canva.jpg"

with open('miniapp/products_db.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

for p in products:
    p['image'] = resolve_card(p.get('title', ''))

with open('miniapp/products_db.json', 'w', encoding='utf-8') as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print("Updated KeyVadi products with clean high-definition cards!")
