import os
import json
import re

LANG_FILE = "user_languages.json"

def get_user_lang(user_id):
    user_id = str(user_id)
    if os.path.exists(LANG_FILE):
        try:
            with open(LANG_FILE, "r", encoding="utf-8") as f:
                langs = json.load(f)
                return langs.get(user_id)
        except:
            pass
    return None

def set_user_lang(user_id, lang):
    user_id = str(user_id)
    langs = {}
    if os.path.exists(LANG_FILE):
        try:
            with open(LANG_FILE, "r", encoding="utf-8") as f:
                langs = json.load(f)
        except:
            pass
    langs[user_id] = lang
    try:
        with open(LANG_FILE, "w", encoding="utf-8") as f:
            json.dump(langs, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def convert_price_to_usd(price_str, rate=33.0):
    try:
        cleaned = price_str.replace("₺", "").replace("TL", "").replace("tl", "").replace(",", ".").strip()
        nums = re.findall(r"\d+(?:\.\d+)?", cleaned)
        if nums:
            val_try = float(nums[0])
            val_usd = val_try / rate
            if val_usd < 1.0:
                return "$0.99"
            else:
                rounded = round(val_usd)
                if rounded < 1:
                    return "$0.99"
                return f"${rounded - 0.01:.2f}"
    except:
        pass
    return "$0.99"
