import os
import glob
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Standard emoji unicode blocks (excluding box drawing characters)
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
    "\U00002702-\U000027B0"  # dingbats
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
    "]+",
    flags=re.UNICODE
)

def audit_all():
    print("=== LAYER 2: TEMPLATES & GROUPS AUDIT ===")
    
    # 1. Audit gruplar.txt
    with open("gruplar.txt", "r", encoding="utf-8") as f:
        groups = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    print(f"1. gruplar.txt count: {len(groups)}")
    unique_groups = set(groups)
    print(f"   Unique groups: {len(unique_groups)}")
    assert len(groups) == 63, f"Expected 63 groups, got {len(groups)}"
    assert len(unique_groups) == 63, "Duplicates found in gruplar.txt"
    print("   [OK] gruplar.txt perfectly intact (63 unique approved groups).")

    # 2. Audit all templates in messages/
    template_files = glob.glob("messages/*.txt") + glob.glob("message_ticaret_*.txt")
    print(f"\n2. Auditing {len(template_files)} template files...")
    
    emoji_fails = []
    greeting_fails = []
    trailing_fails = []
    
    banned_greetings = ["hayırlı geceler", "hayirli geceler", "günaydın", "gunaydin", "iyi akşamlar", "iyi aksamlar", "hayırlı işler", "hayirli isler"]
    
    for tf in template_files:
        with open(tf, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check emojis
        emojis_found = EMOJI_PATTERN.findall(content)
        if emojis_found:
            emoji_fails.append((tf, emojis_found))
            
        # Check greetings
        lower_content = content.lower()
        for bg in banned_greetings:
            if bg in lower_content:
                greeting_fails.append((tf, bg))
                
        # Check trailing lines below bot username
        lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
        bot_line_idx = -1
        for idx, line in enumerate(lines):
            if any(bot in line for bot in ["@KeyVadiSatisBot", "@LisansArenaBot", "@FroxyDestekBOT", "@JarvisCraftsBot"]):
                bot_line_idx = idx
                
        if bot_line_idx != -1 and bot_line_idx < len(lines) - 1:
            # Trailing lines exist after bot line
            trailing_lines = lines[bot_line_idx+1:]
            # Only allow if it's a short footer like closing bracket or disclaimer
            if any(tl.startswith("•") or tl.startswith("»") or "TL" in tl or "₺" in tl for tl in trailing_lines):
                trailing_fails.append((tf, trailing_lines))

    print(f"   Emoji audit: {'[OK] 0 emojis found' if not emoji_fails else f'[FAIL] {emoji_fails}'}")
    print(f"   Greeting audit: {'[OK] 0 fake greetings found' if not greeting_fails else f'[FAIL] {greeting_fails}'}")
    print(f"   Trailing line audit: {'[OK] 0 trailing catalog lines found' if not trailing_fails else f'[FAIL] {trailing_fails}'}")
    
    if emoji_fails or greeting_fails or trailing_fails:
        raise ValueError("Template audit failed!")
    print("   [OK] All template files are 100% clean and correctly formatted.")

if __name__ == '__main__':
    audit_all()
