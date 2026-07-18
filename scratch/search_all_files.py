import os

def search_creator():
    print("Searching for 'creator' in all files in the repository...")
    count = 0
    for root, dirs, files in os.walk("."):
        # Skip git
        if ".git" in root or "__pycache__" in root or ".gemini" in root:
            continue
        for file in files:
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if "creator" in content.lower():
                        count += 1
                        print(f"Found in {path}:")
                        for i, line in enumerate(content.splitlines()):
                            if "creator" in line.lower():
                                print(f"  Line {i+1}: {line.strip()[:100]}")
            except Exception as e:
                pass
    print(f"Search completed. Found in {count} files.")

if __name__ == "__main__":
    search_creator()
