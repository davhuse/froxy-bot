import requests
import asyncio
import os
import sys
from telethon import TelegramClient

API_ID = 26500645
API_HASH = "ca29cb773b400938f3869b2d8e484a0c"
TEST_SESSION = "1BVtsOM4Bu20r41z-Lp0yZ2r9x9iYwPz7M9hYtQ1L5k8vJ3n6u2X8a1b4c7d0e3f" # will load real session

async def main():
    print("--- 1. Testing Live Web Mini App ---")
    res = requests.get("https://bot-service-production-9d74.up.railway.app/jarvis/app", timeout=10)
    print(f"Status Code: {res.status_code}")
    html = res.text

    checks = {
        "JarvisStore/51058105": "https://www.shopier.com/JarvisStore/51058105" in html,
        "JarvisStore/51058117": "https://www.shopier.com/JarvisStore/51058117" in html,
        "JarvisStore/51058118": "https://www.shopier.com/JarvisStore/51058118" in html,
        "JarvisStore/51058119": "https://www.shopier.com/JarvisStore/51058119" in html,
        "JarvisStore/51058120": "https://www.shopier.com/JarvisStore/51058120" in html,
        "JarvisStore/51058121": "https://www.shopier.com/JarvisStore/51058121" in html,
        "Support URL https://t.me/JarvisCraft": "https://t.me/JarvisCraft" in html,
        "No obsolete 32186": "32186" not in html,
        "No obsolete 3051522": "3051522" not in html,
        "No obsolete habil2121": "habil2121" not in html,
        "Orders Card Present": "Siparişlerim & VIP Üyeliklerim" in html
    }

    for desc, passed in checks.items():
        print(f"[{'PASS' if passed else 'FAIL'}] {desc}")

if __name__ == "__main__":
    asyncio.run(main())
