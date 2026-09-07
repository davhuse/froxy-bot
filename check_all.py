import os
corrupted = []
for root, dirs, files in os.walk("."):
    if ".git" in root or "venv" in root: continue
    for file in files:
        if file.endswith((".py", ".txt", ".json", ".html", ".js")):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                if "\ufffd" in content:
                    corrupted.append(filepath)
            except:
                pass
print("Corrupted files:")
for f in corrupted:
    print(f)
