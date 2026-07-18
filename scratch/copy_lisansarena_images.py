import os
import shutil

brain_dir = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d"
static_dir = r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\static"

mappings = {
    "telegram_account_lisansarena_1783811724913.png": "lisansarena_telegram_account.png",
    "perplexity_lisansarena_1783811717551.png": "lisansarena_perplexity_pro.png",
    "deepl_ai_lisansarena_1783811703608.png": "lisansarena_deepl_kisisel.png",
    # We can reuse the same image for both personal and shared
    "deepl_ai_lisansarena_1783811703608.png": "lisansarena_deepl_ortak.png",
    "scribd_lisansarena_1783811696525.png": "lisansarena_scribd_kisisel.png",
    "scribd_lisansarena_1783811696525.png": "lisansarena_scribd_ortak.png",
    "magnific_ai_lisansarena_1783811689649.png": "lisansarena_magnific_ai.png",
    "crunchyroll_mockup_1783810843980.png": "lisansarena_crunchyroll_ozel.png",
    "crunchyroll_mockup_1783810843980.png": "lisansarena_crunchyroll_ortak.png",
    "grammarly_lisansarena_1783811674859.png": "lisansarena_grammarly_haftalik.png",
    "grammarly_lisansarena_1783811674859.png": "lisansarena_grammarly_ortak.png",
}

print("Copying LisansArena cover images to static folder...")
for src_name, dst_name in mappings.items():
    src_path = os.path.join(brain_dir, src_name)
    dst_path = os.path.join(static_dir, dst_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dst_path)
        print(f"Copied: {src_name} -> {dst_name}")
    else:
        # Fallback to copying another if not found, or warn
        print(f"Warning: Source not found: {src_path}")
        
# For mapping duplicates, let's explicitly copy them again to make sure all destination files exist
shutil.copy(os.path.join(brain_dir, "deepl_ai_lisansarena_1783811703608.png"), os.path.join(static_dir, "lisansarena_deepl_kisisel.png"))
shutil.copy(os.path.join(brain_dir, "deepl_ai_lisansarena_1783811703608.png"), os.path.join(static_dir, "lisansarena_deepl_ortak.png"))
shutil.copy(os.path.join(brain_dir, "scribd_lisansarena_1783811696525.png"), os.path.join(static_dir, "lisansarena_scribd_kisisel.png"))
shutil.copy(os.path.join(brain_dir, "scribd_lisansarena_1783811696525.png"), os.path.join(static_dir, "lisansarena_scribd_ortak.png"))
shutil.copy(os.path.join(brain_dir, "crunchyroll_mockup_1783810843980.png"), os.path.join(static_dir, "lisansarena_crunchyroll_ozel.png"))
shutil.copy(os.path.join(brain_dir, "crunchyroll_mockup_1783810843980.png"), os.path.join(static_dir, "lisansarena_crunchyroll_ortak.png"))
shutil.copy(os.path.join(brain_dir, "grammarly_lisansarena_1783811674859.png"), os.path.join(static_dir, "lisansarena_grammarly_haftalik.png"))
shutil.copy(os.path.join(brain_dir, "grammarly_lisansarena_1783811674859.png"), os.path.join(static_dir, "lisansarena_grammarly_ortak.png"))

print("Copy completed successfully.")
