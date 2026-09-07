import json

transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\fbd09d2b-4007-40b6-be24-bbd2f7ab73dc\.system_generated\logs\transcript_full.jsonl"

target_lines = [5967, 5970, 5972, 5975, 5991, 6424, 7103, 8605, 8847, 8851]

with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line_no, line in enumerate(f, 1):
        if line_no in target_lines:
            print(f"=== LINE {line_no} ===")
            try:
                data = json.loads(line)
                print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
            except Exception as e:
                print("Error:", e)
                print(line[:1000])
