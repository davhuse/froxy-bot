# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

path = r'C:\Users\habil\.gemini\antigravity\brain\fbd09d2b-4007-40b6-be24-bbd2f7ab73dc\.system_generated\logs\transcript.jsonl'
with open(path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if '8753762842' in line:
            obj = json.loads(line)
            src = obj.get('source')
            tp = obj.get('type')
            text = str(obj.get('content', ''))
            print(f"Line {i} | Source: {src} | Type: {tp}")
            print("Preview:", text[:400])
            print("="*60)
            if src == 'USER_EXPLICIT' or tp == 'USER_INPUT':
                break
