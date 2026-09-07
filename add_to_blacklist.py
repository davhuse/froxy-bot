import urllib.request
import json
import ssl
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = "https://froxy-bot-kgky.onrender.com"
token = "VOJVbVkVHQBw5J3zI8vQeW2zP5iK6uY9"
headers = {
    "X-Admin-Token": token,
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

groups_to_blacklist = [
    "kod_kupon_alsat",
    "kodkuponcek",
    "kuponindirimsatis",
    "kuponsatimalim",
    "guvenliticaret",
    "kuponindirimpazari",
    "ticaretguvenilir",
    "yucekuponsatis",
    "dijitalpazarlamatr",
    "herkesibeklerimm",
    "kuponkodceksatis",
    "kuponcekkodsatis",
    "referanslinkpaylasimigrup",
    "sosyalmedyaalimsatimticaret",
    "kuponinternet",
    "kuponkodualsat",
    "yemeksepetikuponu",
    "kuponkodmerkez",
    "indirim_kodu",
    "ticaretgrubuuu",
    "ceksatistakasgrup",
    "kodpazari",
    "ticaretcanavari",
    "kuponkodalimsatim",
    "indirimruzgari1",
    "letgoilanlari",
    "ceksat"
]

print(f"Adding {len(groups_to_blacklist)} groups to live blacklist...")
added = 0
for grp in groups_to_blacklist:
    try:
        req = urllib.request.Request(
            f"{base}/api/blacklist/add",
            data=json.dumps({"username": grp}).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            res = json.loads(r.read().decode("utf-8"))
            if res.get("success"):
                added += 1
                print(f"✅ Blacklisted: @{grp}")
            else:
                print(f"⚠️ @{grp}: {res.get('message')}")
    except Exception as e:
        print(f"❌ Error for @{grp}: {e}")

print(f"\nCompleted! {added} groups processed on live server.")

# Also update local blacklist.txt
with open("blacklist.txt", "r", encoding="utf-8") as f:
    current_bl = [line.strip() for line in f if line.strip()]

new_bl = sorted(list(set(current_bl + groups_to_blacklist)), key=lambda x: x.lower())
with open("blacklist.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(new_bl) + "\n")

print(f"Local blacklist.txt updated. Total items: {len(new_bl)}")
