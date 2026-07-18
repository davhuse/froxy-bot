import os
import re

transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\logs\transcript.jsonl"

if not os.path.exists(transcript_path):
    print("Transcript not found at", transcript_path)
else:
    print("Searching transcript for all eyJ strings...")
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                # Search for eyJ followed by base64 chars
                matches = re.findall(r'eyJ[A-Za-z0-9\-_=]{50,}', line)
                if matches:
                    print(f"Line {idx+1}:")
                    for m in set(matches):
                        print(f"  Length: {len(m)} | Token preview: {m[:60]}...")
    except Exception as e:
        print("Error reading transcript:", e)
