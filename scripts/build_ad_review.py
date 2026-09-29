"""Collect the complete Jarvis and KeyVadi advertising rotation for review."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MESSAGES = ROOT / "messages"
OUTPUT = ROOT / "previews" / "reklam-sablonlari.md"

groups = [
    ("JarvisCraft kısa rotasyon", sorted(MESSAGES.glob("jarvis_[1-5].txt"))),
    ("JarvisCraft uzun rotasyon", sorted(MESSAGES.glob("full_jarvis_[1-3].txt"))),
    ("KeyVadi kısa rotasyon", sorted(MESSAGES.glob("keyvadi_*.txt"))),
    ("KeyVadi uzun rotasyon", sorted(MESSAGES.glob("full_keyvadi_[1-5].txt"))),
]

parts = [
    "# JarvisCraft ve KeyVadi reklam şablonları",
    "",
    "Tam metin incelemesi. Fiyatlar yerel katalogdan üretilmiştir; canlı Shopier fiyatı doğrulanamayan ürünler ayrıca kontrol edilmelidir.",
    "",
]
for heading, paths in groups:
    parts += [f"## {heading}", ""]
    for path in paths:
        parts += [f"### {path.name}", "", "```text", path.read_text(encoding="utf-8").rstrip(), "```", ""]

OUTPUT.write_text("\n".join(parts), encoding="utf-8")
print(f"{OUTPUT}: {sum(len(paths) for _, paths in groups)} full templates")
