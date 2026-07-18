with open("blacklist.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()
print(f"Total lines in blacklist.txt: {len(lines)}")
for idx, line in enumerate(lines[:100]):
    print(f"{idx+1}: {line.strip()}")
