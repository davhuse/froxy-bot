# -*- coding: utf-8 -*-
import json
import license_delivery

# Reset stock first to exact test values
stock = {
    "keyvadi_youtube": [
        "2grozvu84t642",
        "2grxvb3fc2rec",
        "2gs6i8mi1cro3"
    ],
    "lisansarena_youtube": [
        "2grkcrd66ws20",
        "2gvic7zfk2tot",
        "2gvzixb57vmva",
        "2gw15erfzyto"
    ]
}
license_delivery.save_licenses_stock(stock)

res_kv1 = license_delivery.allocate_license("YouTube Premium 3 Aylık", brand="keyvadi")
print(f"KeyVadi YT 1 -> allocated: {res_kv1['allocated']}, key: {res_kv1['license_key']}, redeem: {res_kv1['redeem_url']}")

res_la1 = license_delivery.allocate_license("YouTube Premium 3 Aylık Lisans Kodu", brand="lisansarena")
print(f"LisansArena YT 1 -> allocated: {res_la1['allocated']}, key: {res_la1['license_key']}, redeem: {res_la1['redeem_url']}")

res_duo = license_delivery.allocate_license("Duolingo Super 1 Yıllık", brand="keyvadi")
print(f"Duolingo KV -> allocated: {res_duo['allocated']}, needs_email: {res_duo['needs_email']}, note: {res_duo['delivery_note']}")

res_gem = license_delivery.allocate_license("Gemini Pro Davet", brand="lisansarena")
print(f"Gemini LA -> allocated: {res_gem['allocated']}, needs_email: {res_gem['needs_email']}, note: {res_gem['delivery_note']}")

# Put all codes back into licenses.json
stock_final = {
    "canva": ["CANVA-PRO-EDU-KOD-1", "CANVA-PRO-EDU-KOD-2"],
    "adobe": ["ADOBE-CC-PRO-KEY-1", "ADOBE-CC-PRO-KEY-2"],
    "windows": ["W269N-WFGWX-YVC9B-4J6C9-T83GX", "VK7JG-NPHTM-C97JM-9MPGT-3V66T"],
    "office": ["OFFICE-365-PROPLUS-HESAP-1", "OFFICE-365-PROPLUS-HESAP-2"],
    "netflix": ["NETFLIX-4K-UHD-GIRISTOKEN-1"],
    "keyvadi_youtube": [
        "2grozvu84t642",
        "2grxvb3fc2rec",
        "2gs6i8mi1cro3"
    ],
    "lisansarena_youtube": [
        "2grkcrd66ws20",
        "2gvic7zfk2tot",
        "2gvzixb57vmva",
        "2gw15erfzyto"
    ],
    "spotify": ["SPOTIFY-PREM-INVITE-1"],
    "steam": ["STEAM-VIP-RANDOM-KEY-98421", "STEAM-VIP-RANDOM-KEY-11729"],
    "minecraft": ["MC-MIGRATOR-CAPE-CODE-4412", "MC-FOUNDER-CAPE-CODE-8921"],
    "capcut": ["CAPCUT-PRO-PC-1YEAR-TOKEN-1"],
    "exxen": ["EXXEN-REKLAMSIZ-GIRIS-1"],
    "prime": ["PRIME-VIDEO-PREMIUM-1"],
    "hbo": ["HBO-MAX-ULTRAHD-1"],
    "roblox": ["ROBLOX-OFFSALE-ACCOUNT-1"],
    "envato": ["ENVATO-ELEMENTS-TOKEN-1"],
    "freepik": ["FREEPIK-PREMIUM-TOKEN-1"],
    "chatgpt": ["CHATGPT-PLUS-4O-TOKEN-1"]
}
license_delivery.save_licenses_stock(stock_final)
print("Saved final stock successfully!")
