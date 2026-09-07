for fpath in ["froxy_destek_bot.py", "lisansarena_bot.py"]:
    with open(fpath, "r", encoding="utf-8") as f:
        text = f.read()
    new_text = text.replace("froxy-bot-live.onrender.com", "froxy-bot-kgky.onrender.com")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(new_text)
