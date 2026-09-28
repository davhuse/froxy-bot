import re
import py_compile
import sys

with open("otomatik_katil.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add jarviscraft to ACTIVE_ACCOUNT_IDENTITIES
target_id = """    'lisansarenakapali': {
        'stable_name': 'LisansArenaOnline',
        'phone': '14176608361',
        'user_id': 8879941384,
        'slot': 3,
    },"""

replacement_id = """    'lisansarenakapali': {
        'stable_name': 'LisansArenaOnline',
        'phone': '14176608361',
        'user_id': 8879941384,
        'slot': 3,
    },
    'jarviscraft': {
        'stable_name': 'JarvisCraftOnline',
        'phone': '13255674614',
        'user_id': 8387947754,
        'slot': 4,
    },"""
assert target_id in content, "target_id not found"
content = content.replace(target_id, replacement_id)

# 2. Update account_brand and add is_join_only_account
target_brand = """def account_brand(client_name):
    name = (client_name or '').lower()
    if 'lisans' in name or name in {'hesap #3', 'hesap #5'}:
        return 'lisansarena'
    if 'froxy' in name or name in {'hesap #1', 'yerel hesap'}:
        return 'froxy'
    return 'keyvadi'"""

replacement_brand = """def account_brand(client_name):
    name = (client_name or '').lower()
    if 'jarvis' in name or name in {'hesap #4', 'jarviscraftonline'}:
        return 'jarvis'
    if 'lisans' in name or name in {'hesap #3', 'hesap #5'}:
        return 'lisansarena'
    if 'froxy' in name or name in {'hesap #1', 'yerel hesap'}:
        return 'froxy'
    return 'keyvadi'


def is_join_only_account(client_name):
    \"\"\"Accounts configured to only join groups and never send marketing messages.\"\"\"
    cname = get_canonical_account_name(client_name)
    if cname == 'JarvisCraftOnline':
        return True
    configured = os.environ.get("JOIN_ONLY_ACCOUNTS", "").lower()
    return cname.lower() in configured"""
assert target_brand in content, "target_brand not found"
content = content.replace(target_brand, replacement_brand)

# 3. Update get_canonical_account_name and get_account_aliases
target_canon = """def get_canonical_account_name(client_name):
    name = str(client_name or '').strip().lower()
    if 'lisans' in name or name in {'hesap #3', 'hesap #5', 'lisansarenaonline'}:
        return 'LisansArenaOnline'
    if 'froxy' in name or name in {'hesap #1', 'froxyonline', 'froxy_ai', 'c4hex'}:
        return 'FroxyOnline'
    return 'KeyVadiOnline'"""

replacement_canon = """def get_canonical_account_name(client_name):
    name = str(client_name or '').strip().lower()
    if 'jarvis' in name or name in {'hesap #4', 'jarviscraftonline', 'jarviscraft'}:
        return 'JarvisCraftOnline'
    if 'lisans' in name or name in {'hesap #3', 'hesap #5', 'lisansarenaonline'}:
        return 'LisansArenaOnline'
    if 'froxy' in name or name in {'hesap #1', 'froxyonline', 'froxy_ai', 'c4hex'}:
        return 'FroxyOnline'
    return 'KeyVadiOnline'"""
assert target_canon in content, "target_canon not found"
content = content.replace(target_canon, replacement_canon)

target_alias = """    elif cname == 'LisansArenaOnline':
        aliases.add('lisansarenaonline')
        aliases.add('lisansarenadestek')
        aliases.add('lisansarenatr')
    return aliases"""

replacement_alias = """    elif cname == 'LisansArenaOnline':
        aliases.add('lisansarenaonline')
        aliases.add('lisansarenadestek')
        aliases.add('lisansarenatr')
    elif cname == 'JarvisCraftOnline':
        aliases.add('jarviscraft')
        aliases.add('jarviscraftonline')
    return aliases"""
assert target_alias in content, "target_alias not found"
content = content.replace(target_alias, replacement_alias)

# 4. Update get_expected_ad_accounts and BEKLENEN_HESAPLAR
target_exp = """def get_expected_ad_accounts():
    \"\"\"Return the set of ad accounts actively expected to connect.\"\"\"
    expected = {'FroxyOnline', 'KeyVadiOnline'}
    if not is_lisansarena_ad_disabled():
        expected.add('LisansArenaOnline')
    return expected


BEKLENEN_HESAPLAR = {'FroxyOnline', 'KeyVadiOnline', 'LisansArenaOnline'}"""

replacement_exp = """def get_expected_ad_accounts():
    \"\"\"Return the set of ad accounts actively expected to connect.\"\"\"
    expected = {'FroxyOnline', 'KeyVadiOnline'}
    if not is_lisansarena_ad_disabled():
        expected.add('LisansArenaOnline')
    if os.environ.get("AD_STRING_SESSION_JARVIS"):
        expected.add('JarvisCraftOnline')
    return expected


BEKLENEN_HESAPLAR = {'FroxyOnline', 'KeyVadiOnline', 'LisansArenaOnline', 'JarvisCraftOnline'}"""
assert target_exp in content, "target_exp not found"
content = content.replace(target_exp, replacement_exp)

# 5. Update string session loading in main()
target_sessions = """    string_session_key = ""
    string_session_key_2 = ""
    string_session_key_3 = ""
    ad_sleep_min = 600
    ad_sleep_max = 1200
    
    if os.path.exists("bot_config.json"):
        try:
            with open("bot_config.json", "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
                # Render env vars are the durable source of truth. The filesystem
                # is replaced on every deploy and may still contain stale sessions.
                # Uretimde config fallback kullanmak eski User/KeyVadiOnline
                # oturumlarini yeniden canlandirabildigi icin Render yalnizca
                # acikca tanimlanmis ortam degiskenlerini kabul eder.
                is_render_runtime = bool(
                    os.environ.get("RENDER")
                    or os.environ.get("RENDER_SERVICE_ID")
                    or os.environ.get("RENDER_EXTERNAL_URL")
                )
                env_froxy = os.environ.get("AD_STRING_SESSION_FROXY", "").strip()
                env_keyvadi = os.environ.get("AD_STRING_SESSION_KEYVADI", "").strip()
                env_lisans = os.environ.get("AD_STRING_SESSION_LISANSARENA", "").strip()
                if is_render_runtime:
                    string_session_key = env_froxy
                    string_session_key_2 = env_keyvadi
                    string_session_key_3 = env_lisans
                else:
                    string_session_key = env_froxy or cfg.get("string_session_key", "") or cfg.get("ad_string_session", "")
                    string_session_key_2 = env_keyvadi or cfg.get("string_session_key_2", "") or cfg.get("ad_string_session2_final", "") or cfg.get("ad_string_session2_new", "")
                    string_session_key_3 = env_lisans or cfg.get("string_session_key_3", "") or cfg.get("ad_string_session3_final", "") or cfg.get("ad_string_session3_new", "")
                ad_sleep_min = cfg.get("ad_sleep_min", 600)
                ad_sleep_max = cfg.get("ad_sleep_max", 1200)
        except:
            pass"""

replacement_sessions = """    string_session_key = ""
    string_session_key_2 = ""
    string_session_key_3 = ""
    string_session_key_4 = ""
    ad_sleep_min = 600
    ad_sleep_max = 1200
    
    if os.path.exists("bot_config.json"):
        try:
            with open("bot_config.json", "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
                # Render env vars are the durable source of truth. The filesystem
                # is replaced on every deploy and may still contain stale sessions.
                # Uretimde config fallback kullanmak eski User/KeyVadiOnline
                # oturumlarini yeniden canlandirabildigi icin Render yalnizca
                # acikca tanimlanmis ortam degiskenlerini kabul eder.
                is_render_runtime = bool(
                    os.environ.get("RENDER")
                    or os.environ.get("RENDER_SERVICE_ID")
                    or os.environ.get("RENDER_EXTERNAL_URL")
                    or os.environ.get("RAILWAY_ENVIRONMENT")
                )
                env_froxy = os.environ.get("AD_STRING_SESSION_FROXY", "").strip()
                env_keyvadi = os.environ.get("AD_STRING_SESSION_KEYVADI", "").strip()
                env_lisans = os.environ.get("AD_STRING_SESSION_LISANSARENA", "").strip()
                env_jarvis = os.environ.get("AD_STRING_SESSION_JARVIS", "").strip()
                if is_render_runtime:
                    string_session_key = env_froxy
                    string_session_key_2 = env_keyvadi
                    string_session_key_3 = env_lisans
                    string_session_key_4 = env_jarvis
                else:
                    string_session_key = env_froxy or cfg.get("string_session_key", "") or cfg.get("ad_string_session", "")
                    string_session_key_2 = env_keyvadi or cfg.get("string_session_key_2", "") or cfg.get("ad_string_session2_final", "") or cfg.get("ad_string_session2_new", "")
                    string_session_key_3 = env_lisans or cfg.get("string_session_key_3", "") or cfg.get("ad_string_session3_final", "") or cfg.get("ad_string_session3_new", "")
                    string_session_key_4 = env_jarvis or cfg.get("string_session_key_4", "")
                ad_sleep_min = cfg.get("ad_sleep_min", 600)
                ad_sleep_max = cfg.get("ad_sleep_max", 1200)
        except:
            pass"""
assert target_sessions in content, "target_sessions not found"
content = content.replace(target_sessions, replacement_sessions)

# 6. Add Client 4 connect block in main()
target_c3_end = """        update_ad_account_status(
            'LisansArenaOnline',
            process_running=True,
            telegram_connected=False,
            telegram_authorized=False,
            phase='disabled_by_config',
            last_error='LisansArena reklam hesabi 13 Eylul saat 12:00 itibariyla otomatik acilacak.',
            next_blast_at=None,
        )"""

replacement_c4 = """        update_ad_account_status(
            'LisansArenaOnline',
            process_running=True,
            telegram_connected=False,
            telegram_authorized=False,
            phase='disabled_by_config',
            last_error='LisansArena reklam hesabi 13 Eylul saat 12:00 itibariyla otomatik acilacak.',
            next_blast_at=None,
        )

    # Client 4 (JarvisCraft - Sadece gruplara katılır, reklam mesajı atmaz)
    if string_session_key_4:
        print("🔑 4. Hesap (JarvisCraft): StringSession kullanılarak bağlanılıyor...")
        try:
            from telethon.sessions import StringSession
            client4 = TelegramClient(StringSession(string_session_key_4), api_id, api_hash, timeout=20, connection_retries=-1, auto_reconnect=True, flood_sleep_threshold=5)
            await client4.connect()
            if await client4.is_user_authorized():
                me = await client4.get_me()
                active_clients.append((client4, "Hesap #4", {"id": me.id, "slot": 4}))
                print(f"✅ 4. Hesap (JarvisCraft) yetkilendirildi. ID: {me.id} (@{me.username})")
            else:
                print("❌ HATA: 4. Hesap (JarvisCraft) yetkilendirilmemiş!")
        except Exception as e:
            report_client_error(4, e)
            try:
                await client4.disconnect()
            except Exception:
                pass"""
assert target_c3_end in content, "target_c3_end not found"
content = content.replace(target_c3_end, replacement_c4)

# 7. Join-only mode in ad_worker
target_worker_blast = """            sent_count = 0
            fail_count = 0

            if defer_for_floor or not blast_targets:"""

replacement_worker_blast = """            sent_count = 0
            fail_count = 0

            if is_join_only_account(client_name):
                print(f"[{client_name}] 🛡️ SADECE GRUBA KATILMA MODU AKTİF! Reklam/mesaj gönderimi kapalı.")
                blast_targets = []

            if defer_for_floor or not blast_targets:"""
assert target_worker_blast in content, "target_worker_blast not found"
content = content.replace(target_worker_blast, replacement_worker_blast)

with open("otomatik_katil.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied successfully! Compiling to verify...")
py_compile.compile("otomatik_katil.py", doraise=True)
print("SUCCESS: otomatik_katil.py compiled with zero syntax errors!")
