import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

file_path = "otomatik_katil.py"

with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

new_blast_tracking_code = '''def get_canonical_account_name(client_name):
    name = str(client_name or '').strip().lower()
    if 'lisans' in name or name in {'hesap #3', 'hesap #5', 'lisansarenaonline'}:
        return 'LisansArenaOnline'
    if 'froxy' in name or name in {'hesap #1', 'froxyonline', 'froxy_ai', 'c4hex'}:
        return 'FroxyOnline'
    return 'KeyVadiOnline'

def get_account_aliases(client_name):
    cname = get_canonical_account_name(client_name)
    aliases = {cname, client_name, client_name.lower()}
    if cname == 'FroxyOnline':
        aliases.update({'Hesap #1', 'froxy_ai', 'froxyonline', 'c4hex'})
    elif cname == 'KeyVadiOnline':
        aliases.update({'Hesap #2', 'keyvadionline', 'keyvadidestek'})
    elif cname == 'LisansArenaOnline':
        aliases.update({'Hesap #3', 'lisansarenaonline'})
    return aliases

def save_last_blast_time(client_name):
    """Hesabın son blast tamamlanma zamanını kaydeder (tüm rumuzlar için)"""
    try:
        from datetime import datetime
        cname = get_canonical_account_name(client_name)
        cooldowns = load_cooldowns()
        now_str = datetime.now().isoformat()
        for alias in get_account_aliases(client_name):
            cooldowns[f"__LAST_BLAST_TIME_{alias}"] = now_str
        save_cooldowns(cooldowns)
        try:
            fs_set_state(cooldowns=json.dumps(cooldowns, ensure_ascii=False, indent=2))
        except Exception:
            pass
        print(f"[{cname}] 💾 Son blast zamanı kaydedildi: {now_str}")
    except Exception as e:
        print(f"[{client_name}] ⚠️ Son blast zamanı kaydetme hatası: {e}")

def get_last_blast_remaining_wait(client_name, target_wait_seconds=3600):
    """Sunucu yeniden başlatıldığında hesabın kalan bekleme süresini hesaplar"""
    try:
        from datetime import datetime
        cname = get_canonical_account_name(client_name)
        cooldowns = load_cooldowns()
        
        fs_cdata = {}
        try:
            _, _, _, _, fs_cooldowns, _ = fs_get_state()
            if fs_cooldowns:
                fs_cdata = json.loads(fs_cooldowns)
        except Exception:
            pass

        timestamps = []
        for alias in get_account_aliases(client_name):
            k = f"__LAST_BLAST_TIME_{alias}"
            val = cooldowns.get(k) or fs_cdata.get(k)
            if val and isinstance(val, str):
                try:
                    timestamps.append(datetime.fromisoformat(val))
                except Exception:
                    pass

        if not timestamps:
            print(f"[{cname}] 🛡️ Sunucu başlangıcı: Son blast kaydı bulunamadı, 60 dakika güvenlik beklemesi uygulanıyor.")
            return target_wait_seconds

        latest_dt = max(timestamps)
        elapsed = (datetime.now() - latest_dt).total_seconds()
        if elapsed < target_wait_seconds:
            rem = int(target_wait_seconds - elapsed)
            print(f"[{cname}] ⏳ Son blast {int(elapsed // 60)}dk önce yapılmış → Kalan {int(rem // 60)}dk ({rem}sn) bekleniyor.")
            return rem
        else:
            print(f"[{cname}] ✅ Son blast {int(elapsed // 60)}dk önce yapılmış (1 saat doldu), yeni blast zamanı geldi.")
            return 0
    except Exception as e:
        print(f"[{client_name}] ⚠️ Kalan bekleme hesaplama hatası: {e}")
        return target_wait_seconds'''

old_func_pattern = r'def save_last_blast_time\(client_name\):[\s\S]*?return target_wait_seconds'

if re.search(old_func_pattern, code):
    code = re.sub(old_func_pattern, new_blast_tracking_code, code)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)
    print("SUCCESS: Upgraded blast tracking & cooldown memory in otomatik_katil.py!")
else:
    print("WARNING: Pattern not matched in otomatik_katil.py!")
