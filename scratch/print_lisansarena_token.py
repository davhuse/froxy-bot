with open(r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\logs\transcript.jsonl", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if idx + 1 == 11944:
            import re
            matches = re.findall(r'eyJ0eXAi[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+', line)
            if matches:
                print("Found LisansArena token:")
                print(matches[0])
            break
