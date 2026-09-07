import json
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\fbd09d2b-4007-40b6-be24-bbd2f7ab73dc\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line_no, line in enumerate(f, 1):
        if line_no in (5967, 5970, 5972, 5975, 5976):
            print(f"=== LINE {line_no} ===")
            obj = json.loads(line)
            print(obj.get("content") or obj.get("tool_calls"))
