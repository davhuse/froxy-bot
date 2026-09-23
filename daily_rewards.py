import os
import json
import time
import random
import logging

logger = logging.getLogger(__name__)

DAILY_BOX_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily_box_claims.json")

def _load_claims():
    if os.path.exists(DAILY_BOX_FILE):
        try:
            with open(DAILY_BOX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load daily box claims: {e}")
    return {}

def _save_claims(data):
    try:
        temp = f"{DAILY_BOX_FILE}.tmp"
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp, DAILY_BOX_FILE)
    except Exception as e:
        logger.warning(f"Failed to save daily box claims: {e}")

def claim_daily_reward(user_id):
    """
    Kullanici icin 24 saatte 1 kez acilabilen gunluk sans kasasi.
    Geriye kazanilan odulu ve kalan sure bilgisini dondurur.
    """
    uid = str(user_id)
    now = int(time.time())
    claims = _load_claims()
    user_record = claims.get(uid, {})
    last_claim = user_record.get("last_claim", 0)

    cooldown_seconds = 24 * 3600
    elapsed = now - last_claim

    if elapsed < cooldown_seconds:
        remaining = cooldown_seconds - elapsed
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        return {
            "eligible": False,
            "remaining_seconds": remaining,
            "remaining_text": f"{hours} saat {minutes} dakika",
            "last_code": user_record.get("last_code", "")
        }

    # Sans kasasi odul olasiliklari
    roll = random.random()
    if roll < 0.45:
        reward = {
            "win": True,
            "code": "FLAS15",
            "title": "%15 Shopier Indirim Kuponu",
            "message": "Tebrikler! Gunluk kasanizdan tum urunlerde gecerli %15 indirim kodu cikti.\n\nIndirim Kodu: FLAS15\n(Shopier odeme ekraninda kupon kismina girerek aninda %15 indirimle satin alabilirsiniz)"
        }
    elif roll < 0.85:
        reward = {
            "win": True,
            "code": "GERİGEL10",
            "title": "%10 Shopier Indirim Kuponu",
            "message": "Tebrikler! Gunluk kasanizdan tum urunlerde gecerli %10 indirim kodu cikti.\n\nIndirim Kodu: GERİGEL10\n(Shopier odeme sayfasinda kupon alanina yazarak %10 indirimden aninda yararlanabilirsiniz)"
        }
    else:
        reward = {
            "win": False,
            "code": "",
            "title": "Bos Kasa",
            "message": "Bugun kasanizdan indirim cikmadi. Sansinizi yarin tekrar deneyebilirsiniz!"
        }

    claims[uid] = {
        "last_claim": now,
        "total_claims": user_record.get("total_claims", 0) + 1,
        "last_code": reward.get("code", "")
    }
    _save_claims(claims)

    return {
        "eligible": True,
        "reward": reward
    }
