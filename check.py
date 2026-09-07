with open("lisansarena_bot.py", "rb") as f:
    text = f.read().decode("utf-8", errors="replace")
    if "\ufffd" in text:
        print("YES! Corrupted characters found in lisansarena_bot.py")
    else:
        print("No corruption found.")
