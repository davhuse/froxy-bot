with open("froxy_destek_bot.py", "rb") as f:
    text = f.read().decode("utf-8", errors="replace")
    if "" in text:
        print("YES! Corrupted characters found in froxy_destek_bot.py")
    else:
        print("No corruption found.")
