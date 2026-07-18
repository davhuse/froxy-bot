import json
import re

transcript_path = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d\.system_generated\logs\transcript.jsonl"
prompts = {}

with open(transcript_path, "r", encoding="utf-8") as f:
    for line_idx, line in enumerate(f):
        try:
            data = json.loads(line)
            tool_calls = data.get("tool_calls", [])
            for tc in tool_calls:
                if tc.get("name") == "generate_image":
                    args = tc.get("args", {})
                    name = args.get("ImageName")
                    prompt = args.get("Prompt")
                    if name and prompt:
                        # Unquote and clean
                        name = name.strip('"').strip("'")
                        prompt = prompt.strip('"').strip("'")
                        prompts[name] = prompt
        except Exception:
            pass

print(f"Extracted {len(prompts)} prompts:")
for k, v in prompts.items():
    print(f"[{k}] -> {v}\n")
