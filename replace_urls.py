import os

for root, dirs, files in os.walk("."):
    if "node_modules" in root or ".git" in root or "venv" in root or "__pycache__" in root:
        continue
    for file in files:
        if file.endswith(".py") or file.endswith(".json") or file.endswith(".html") or file.endswith(".js"):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                new_content = content.replace("froxy-bot-live-r5se.onrender.com", "froxy-bot-live-r5se.onrender.com")
                new_content = new_content.replace("froxy-bot-live-r5se.onrender.com", "froxy-bot-live-r5se.onrender.com")
                new_content = new_content.replace("froxy-bot-live-r5se.onrender.com", "froxy-bot-live-r5se.onrender.com")
                
                if new_content != content:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"Updated {filepath}")
            except Exception as e:
                print(f"Failed {filepath}: {e}")
