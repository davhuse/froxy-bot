import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("froxy_session_output.txt", "r", encoding="utf-8") as f:
    s_froxy = f.read().strip()

def get_master_known():
    known = set()
    for fname in os.listdir("."):
        if not (fname.endswith(".json") or fname.endswith(".txt")):
            continue
        if fname in ["yeni_birebir_hedef_gruplar.json", "yeni_birebir_hedef_gruplar.txt"]:
            continue
        fpath = os.path.join(".", fname)
        try:
            if fname.endswith(".json"):
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, str):
                                u = item.strip().lower().lstrip("@")
                                if 3 < len(u) < 35:
                                    known.add(u)
                            elif isinstance(item, dict):
                                for k in ["username", "group", "id", "chat_id", "link"]:
                                    v = item.get(k)
                                    if v and isinstance(v, str):
                                        u = v.strip().lower().lstrip("@").replace("https://t.me/", "")
                                        if 3 < len(u) < 35:
                                            known.add(u)
                    elif isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(k, str) and 3 < len(k) < 35:
                                known.add(k.strip().lower().lstrip("@"))
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict):
                                        for subk in ["username", "group", "link"]:
                                            subv = item.get(subk)
                                            if subv and isinstance(subv, str):
                                                u = subv.strip().lower().lstrip("@").replace("https://t.me/", "")
                                                if 3 < len(u) < 35:
                                                    known.add(u)
                                    elif isinstance(item, str):
                                        u = item.strip().lower().lstrip("@")
                                        if 3 < len(u) < 35:
                                            known.add(u)
            elif fname.endswith(".txt"):
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        for m in re.finditer(r"(?:t\.me/|@|^|\s)([a-zA-Z0-9_]{4,32})", line):
                            u = m.group(1).lower()
                            if u not in {"joinchat", "share", "proxy", "http", "https", "true", "false", "none"}:
                                known.add(u)
        except Exception:
            pass
    return known

SEED_GROUPS = [
    "kuponsat", "kuponhesapsatis", "ceksat", "letgoilanlari", "kuponsatisgrup",
    "alimsatimmerkezii", "ticaretyapn", "kodkuponmarketi", "yucekuponsatis",
    "ceksatkupon", "wishx_2", "zeroticaret", "ticaretgruptr", "kuponkodceksatis",
    "kodpazari", "YemekSepetiKuponu", "KodKuponMerkezi", "kuponkodmerkez",
    "herkesibeklerimm", "kuponyaticaret", "cek_kupon_kod_ilan", "Minakuponkodsatis",
    "kinseimedyaticaret", "dijitalticaretgrubu", "aTicaret", "mailalimsatimticaret",
    "satiskodtakasi", "kuponkodalimsatimm", "kuponindirimpazari", "mukyemek",
    "kuponvekodsatisgrubu", "kodmalf", "indirimruzgari1", "kuponindirimkodalisveris",
    "uygunkod", "kodalimsatim", "kuponalsatgurup", "bedavainternetkodalimsatim",
    "bedavainternetkod", "kuponindirimlisatis", "kuponceking", "me7alimsatim"
]

async def harvest_candidates():
    master_known = get_master_known()
    print(f"Master known count: {len(master_known)}")
    
    client = TelegramClient(StringSession(s_froxy), API_ID, API_HASH)
    await client.connect()
    me = await client.get_me()
    print(f"Connected as {me.first_name}")
    
    raw_candidates = {}
    
    for s_idx, sg in enumerate(SEED_GROUPS, 1):
        try:
            e = await client.get_entity(sg)
            msgs = await client.get_messages(e, limit=300)
            print(f"[{s_idx}/{len(SEED_GROUPS)}] Seed: @{sg} -> Fetched {len(msgs)} messages")
            for m in msgs:
                if not m:
                    continue
                # 1. From text
                if m.text:
                    for found in re.finditer(r"(?:t\.me/|@)([a-zA-Z0-9_]{4,32})", m.text):
                        u = found.group(1).lower()
                        if u not in master_known and u not in {
                            "joinchat", "share", "proxy", "bot", "channel", "http", "https", "support",
                            "admin", "destek", "yardim", "iletisim", "reklam", "contact", "duyuru"
                        }:
                            if u not in raw_candidates:
                                raw_candidates[u] = []
                            raw_candidates[u].append({
                                "found_in": sg,
                                "date": m.date,
                                "sender_id": m.sender_id,
                                "text": m.text[:120].replace("\n", " ")
                            })
                # 2. From forward header
                if m.fwd_from and m.fwd_from.from_id:
                    # check peer channel
                    pass
            await asyncio.sleep(0.3)
        except Exception as ex:
            print(f"Seed @{sg} err: {ex}")
            
    print(f"\n[*] Toplam Benzersiz Yeni Aday Sayısı: {len(raw_candidates)}")
    with open("extracted_raw_candidates.json", "w", encoding="utf-8") as f:
        json.dump(raw_candidates, f, ensure_ascii=False, indent=2, default=str)
    print("[*] Kaydedildi: extracted_raw_candidates.json")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(harvest_candidates())
