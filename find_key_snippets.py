import json
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\fbd09d2b-4007-40b6-be24-bbd2f7ab73dc\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line_no, line in enumerate(f, 1):
        if "FIREBASE_API_KEY" in line:
            print(f"--- Line {line_no} (FIREBASE_API_KEY) ---")
            idx = 0
            while True:
                idx = line.find("FIREBASE_API_KEY", idx)
                if idx == -1: break
                print("Snippet:", line[max(0, idx-50): min(len(line), idx+200)])
                idx += 16
        if "SHOPIER_KEYVADI_ACCESS_TOKEN" in line:
            print(f"--- Line {line_no} (SHOPIER_KEYVADI_ACCESS_TOKEN) ---")
            idx = 0
            while True:
                idx = line.find("SHOPIER_KEYVADI_ACCESS_TOKEN", idx)
                if idx == -1: break
                print("Snippet:", line[max(0, idx-50): min(len(line), idx+200)])
                idx += 28
