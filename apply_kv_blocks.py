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

# 1. Original global blacklist
original_bl = [
    "-1001572316417",
    "-1572316417",
    "Gurcistanticaret",
    "buradayiztikla",
    "dolapilanlari",
    "froxyreferans",
    "ilanticaret",
    "illegalalimsatimerkezi",
    "keyvadireferans",
    "kuponkodalsat",
    "lisansarenareferans",
    "referansreklam1",
    "referansreklamyardimlasma",
    "reklamonliene",
    "reklamreferans",
    "reklamvereferanss",
    "sanalalimsatimticaret",
    "sultanbeyliikinciel0",
    "takipcisatiyor",
    "ticar4t",
    "ticaretyapreklam",
    "ttingalimsatim",
    "ticaretforumofficial",
    "kuponceksatis",
    "kuponceksatisi",
    "kuponceksatistv",
    "kuponsat",
    "kodpazari",
    "kuponindirimlisatis",
    "kuponsatimalim",
    "polat7272",
    "5112921888"
]

with open("blacklist.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(original_bl) + "\n")

print("Reverted local blacklist.txt to 32 items.")

# 2. Update Firestore / live blacklist to original
try:
    API_KEY = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
    PROJECT_ID = "bot-2-63772"
    url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/reklam/state?updateMask.fieldPaths=blacklist_list&key={API_KEY}"
    blacklist_content = '\n'.join(original_bl) + '\n'
    fields = {"blacklist_list": {"stringValue": blacklist_content}}
    req = urllib.request.Request(url, data=json.dumps({"fields": fields}).encode('utf-8'), headers={"Content-Type": "application/json"}, method="PATCH")
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        print("Live Firestore blacklist restored to original 32 items.")
except Exception as e:
    print("Firestore update error:", e)

# 3. Add KeyVadi-specific blocks to account_group_blocks.json
kv_blocks = {
    "kod_kupon_alsat": "UserBannedInChannel",
    "kodkuponcek": "UserBannedInChannel",
    "kuponindirimsatis": "UserBannedInChannel",
    "kuponsatimalim": "UserBannedInChannel",
    "guvenliticaret": "ChatWriteForbidden",
    "kuponindirimpazari": "ChatWriteForbidden",
    "ticaretguvenilir": "ChatWriteForbidden",
    "yucekuponsatis": "ModerationDeleted",
    "dijitalpazarlamatr": "BadRequestError",
    "herkesibeklerimm": "invalid_invite",
    "kuponkodceksatis": "invalid_invite",
    "kuponcekkodsatis": "invalid_invite",
    "referanslinkpaylasimigrup": "UsernameInvalidError",
    "sosyalmedyaalimsatimticaret": "UsernameInvalidError",
    "ceksat": "UserBannedInChannel"
}

blocks = {}
try:
    with open("account_group_blocks.json", "r", encoding="utf-8") as f:
        blocks = json.load(f)
except Exception:
    pass

for grp, reason in kv_blocks.items():
    grp_clean = grp.lower().replace("@", "")
    entry = blocks.setdefault(grp_clean, {})
    entry["KeyVadiOnline"] = {
        "reason": reason,
        "date": "2026-09-03T21:30:00+00:00"
    }

with open("account_group_blocks.json", "w", encoding="utf-8") as f:
    json.dump(blocks, f, indent=2, ensure_ascii=False)

print(f"Updated account_group_blocks.json with {len(kv_blocks)} KeyVadi-specific blocks!")
