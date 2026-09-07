import json

with open("bot_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

config["froxy_bot_running"] = False
config["ad_bot_running"] = False
config["support_bot_running"] = False
config["lisansarena_bot_running"] = False

with open("bot_config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, indent=4)
