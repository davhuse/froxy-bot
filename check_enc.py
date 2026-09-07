import chardet
with open("froxy_destek_bot.py", "rb") as f:
    print(chardet.detect(f.read()))
