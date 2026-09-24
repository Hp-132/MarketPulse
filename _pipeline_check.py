import json
from pathlib import Path

raw_dir = Path("data/raw")
files = sorted(f for f in raw_dir.iterdir() if f.suffix == ".json")
print(f"Found {len(files)} JSON files in data/raw/\n")
total = 0
for f in files:
    data = json.loads(f.read_text(encoding="utf-8"))
    total += len(data)
    print(f"  {f.name:<40}  {len(data):>4} records")
print(f"\n  TOTAL: {total} records across all files")
