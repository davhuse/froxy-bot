import os

brain_dir = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d"

print("Listing all files in brain directory matching 'lisansarena' or 'mockup' or 'exxen' or 'trendyol' or 'shell' or 'steam' or 'office':")
keywords = ["lisansarena", "mockup", "exxen", "trendyol", "shell", "steam", "office"]
count = 0
for f in os.listdir(brain_dir):
    f_lower = f.lower()
    for kw in keywords:
        if kw in f_lower:
            size = os.path.getsize(os.path.join(brain_dir, f))
            print(f"- {f} ({size} bytes)")
            count += 1
            break
            
print(f"Total matching files: {count}")
