with open(r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\scratch\create_target_lisansarena_products.py", "r", encoding="utf-8") as f:
    lines1 = f.readlines()
with open(r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\scratch\refresh_shopier_images.py", "r", encoding="utf-8") as f:
    lines2 = f.readlines()

token1 = ""
for line in lines1:
    if line.startswith("token ="):
        token1 = line.split("=")[1].strip().strip('"')
        break

token2 = ""
for line in lines2:
    if line.startswith("token ="):
        token2 = line.split("=")[1].strip().strip('"')
        break

print("Token lengths:")
print(f"Token 1 (create):  {len(token1)}")
print(f"Token 2 (refresh): {len(token2)}")
print(f"Are they identical? {token1 == token2}")

if token1 != token2:
    print("Mismatches:")
    min_len = min(len(token1), len(token2))
    for idx in range(min_len):
        if token1[idx] != token2[idx]:
            print(f"Index {idx}: Token 1 has '{token1[idx]}', Token 2 has '{token2[idx]}'")
            print("Token 1 context:", token1[max(0, idx-10):idx+10])
            print("Token 2 context:", token2[max(0, idx-10):idx+10])
            break
