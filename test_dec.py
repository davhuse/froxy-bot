with open("froxy_destek_bot.py", "rb") as f:
    data = f.read()
    try:
        data.decode("utf-8")
        print("UTF-8 works")
    except Exception as e:
        print("UTF-8 error:", e)
    try:
        data.decode("windows-1254")
        print("windows-1254 works")
    except Exception as e:
        print("windows-1254 error:", e)
