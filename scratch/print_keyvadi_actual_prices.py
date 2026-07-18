import csv
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

print("KeyVadi CSV products and prices:")
with open("shopier_urunler.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    for idx, row in enumerate(reader):
        if not row:
            continue
        row_str = " | ".join(row)
        cols = row_str.split(";")
        if len(cols) >= 2:
            print(f"{idx}: {cols[0]} -> {cols[1]} TRY")
