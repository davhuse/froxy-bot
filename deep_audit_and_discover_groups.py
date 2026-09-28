import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel, Chat

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

SEARCH_QUERIES = [
    "kupon satış", "kupon kod", "indirim kodu", "indirim kupon",
    "hesap satış", "dijital lisans", "alım satım ticaret", "market kupon",
    "yemeksepeti kupon", "trendyol indirim", "sanal ticaret", "dijital pazar"
]

NEGATIVE_TERMS = {
    "bahis", "casino", "slot", "rulet", "iddaa", "porn", "ifsa", "ifşa",
    "escort", "papara", "yasadisi", "yasadışı", "hack", "warez", "cc",
    "dolandirici", "dolandırıcı", "sweet bonanza", "gates of olympus", "kumar"
}

POSITIVE_TERMS = {
    "kupon", "kod", "indirim", "hesap", "ticaret", "satis", "satış",
    "alim", "alım", "market", "yemek", "lisans", "fiyat", "stok",
    "kampanya", "alisveris", "alışveriş", "çek", "cek", "takas", "pazar",
    "dijital", "premium", "epin", "shopier"
}

async def audit_group(client, username_or_entity):
    try:
        entity = await client.get_entity(username_or_entity)
    except Exception as e:
        return {"ok": False, "reason": f"get_entity_error: {type(e).__name__}"}

    # 1. Type check
    if getattr(entity, 'broadcast', False) and not getattr(entity, 'megagroup', False):
        return {"ok": False, "reason": "broadcast_channel"}
    if not getattr(entity, 'megagroup', False) and not isinstance(entity, Chat):
        return {"ok": False, "reason": "not_a_megagroup"}

    username = getattr(entity, 'username', '') or ''
    title = getattr(entity, 'title', '') or ''
    title_lower = title.lower()

    # 2. Title negative check
    for neg in NEGATIVE_TERMS:
        if neg in title_lower:
            return {"ok": False, "reason": f"negative_in_title: {neg}"}

    # 3. Write permission check
    banned = getattr(entity, 'default_banned_rights', None)
    if banned and banned.send_messages:
        return {"ok": False, "reason": "send_messages_restricted"}

    # 4. Member count
    try:
        full = await client(GetFullChannelRequest(entity))
        members = full.full_chat.participants_count
        slowmode = getattr(full.full_chat, 'slowmode_seconds', 0) or 0
    except Exception:
        members = getattr(entity, 'participants_count', 0) or 0
        slowmode = 0

    if members < 80:
        return {"ok": False, "reason": f"low_members: {members}"}

    # 5. Fetch inside messages
    try:
        messages = await client.get_messages(entity, limit=20)
    except Exception as e:
        return {"ok": False, "reason": f"get_messages_error: {type(e).__name__}"}

    if not messages or len(messages) < 3:
        return {"ok": False, "reason": f"insufficient_messages: {len(messages) if messages else 0}"}

    # 6. Activity / Freshness check
    now = datetime.now(timezone.utc)
    newest_msg = messages[0]
    msg_date = newest_msg.date
    days_old = (now - msg_date).days
    if days_old > 7:
        return {"ok": False, "reason": f"inactive_group_last_msg_{days_old}_days_ago"}

    # 7. Sender diversity check
    senders = {m.sender_id for m in messages if getattr(m, 'sender_id', None)}
    if len(messages) >= 10 and len(senders) < 2:
        return {"ok": False, "reason": f"single_sender_abandoned"}

    # 8. Content inspection for negative terms and positive commerce terms
    all_text = " ".join((m.raw_text or '') for m in messages).lower()
    
    for neg in NEGATIVE_TERMS:
        if neg in all_text:
            return {"ok": False, "reason": f"negative_term_in_messages: {neg}"}

    positive_matches = [pos for pos in POSITIVE_TERMS if pos in title_lower or pos in all_text]
    if len(positive_matches) < 2:
        return {"ok": False, "reason": f"lacks_positive_commerce_terms: {positive_matches}"}

    return {
        "ok": True,
        "username": username,
        "title": title,
        "members": members,
        "slowmode": slowmode,
        "last_message_date": str(msg_date),
        "days_since_last_msg": days_old,
        "sample_msg": (newest_msg.raw_text or '')[:100].replace("\n", " "),
        "positive_matches": positive_matches[:5],
    }

async def run_discovery_and_audit():
    with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
        session_str = f.read().strip()

    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Telegram oturumu yetkisiz!", flush=True)
        return

    me = await client.get_me()
    print(f"Denetim Hesabi: {me.first_name} (@{me.username or me.id})", flush=True)

    # Mevcut gruplari yukle
    with open("gruplar.txt", "r", encoding="utf-8") as f:
        existing = {line.strip().lower().lstrip('@') for line in f if line.strip()}
    print(f"Mevcut gruplar.txt grup sayisi: {len(existing)}", flush=True)

    # 1. Global aramadan aday topla
    discovered_candidates = set()
    print("\n--- Telegram Global Arama ile Canli Grup Adayi Toplama ---", flush=True)
    for q in SEARCH_QUERIES:
        try:
            res = await client(SearchRequest(q=q, limit=20))
            for chat in res.chats:
                u = getattr(chat, 'username', '')
                if u and u.lower() not in existing:
                    discovered_candidates.add(u.lower())
            print(f"  Query '{q}': Toplam aday havuzu simdi {len(discovered_candidates)}", flush=True)
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"  Query '{q}' hata: {e}", flush=True)

    # 2. Dosyalardaki 448 filtrelenmis anahtar kelime adaylarini ekle
    candidate_files = [
        '100_kesin_onayli_kupon_kod_gruplari.json',
        'derin_kesif_onayli_yeni_gruplar.json',
        'all_trader_active_groups.json',
        'fresh_candidates_to_audit.json'
    ]
    keywords = ['kupon', 'indirim', 'kod', 'ticaret', 'pazar', 'alisveris', 'satis', 'alsat', 'firsat', 'kampanya', 'market', 'yemek', 'bakiye', 'hesap', 'lisans', 'takas']
    for fn in candidate_files:
        if os.path.exists(fn):
            try:
                with open(fn, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    items = list(d.keys()) if isinstance(d, dict) else d
                    for item in items:
                        if isinstance(item, dict):
                            item = item.get('username') or ''
                        m = re.findall(r'[a-zA-Z][a-zA-Z0-9_]{3,31}', str(item))
                        for u in m:
                            u_low = u.lower()
                            if u_low not in existing and any(k in u_low for k in keywords):
                                discovered_candidates.add(u_low)
            except Exception:
                pass

    print(f"\nToplam denetlenecek tekil aday sayisi: {len(discovered_candidates)}", flush=True)

    approved_groups = []
    if os.path.exists("deep_verified_groups.json"):
        try:
            with open("deep_verified_groups.json", "r", encoding="utf-8") as f:
                approved_groups = json.load(f)
        except:
            approved_groups = []
    approved_usernames = {g['username'].lower() for g in approved_groups if 'username' in g}

    audited_count = 0

    print("\n--- Tek Tek Grup Icine Girerek Derinlemesine Denetim Basliyor ---\n", flush=True)
    for u in sorted(list(discovered_candidates)):
        if u in approved_usernames:
            continue
        audited_count += 1
        res = await audit_group(client, u)
        if res["ok"]:
            print(f"  [ONAYLANDI] @{res['username']:<25} | {res['members']} üye | Son mesaj: {res['days_since_last_msg']} gün önce | Başlık: {res['title']}", flush=True)
            approved_groups.append(res)
            approved_usernames.add(res['username'].lower())
            with open("deep_verified_groups.json", "w", encoding="utf-8") as f:
                json.dump(approved_groups, f, ensure_ascii=False, indent=2)
            if len(approved_groups) >= 20:
                print(f"\n20 kaliteli yeni onayli grup hedefine ulasildi!", flush=True)
                break
        else:
            if audited_count % 10 == 0:
                print(f"  ... {audited_count}/{len(discovered_candidates)} grup denetlendi, {len(approved_groups)} onaylandi (Son elenen: @{u}: {res['reason']}) ...", flush=True)
        await asyncio.sleep(0.3)

    await client.disconnect()

    print(f"\nDenetim Bitti! Toplam Onaylanan Kaliteli Ticaret Grubu: {len(approved_groups)}", flush=True)

if __name__ == "__main__":
    asyncio.run(run_discovery_and_audit())
