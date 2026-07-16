"""
backfill_discount.py
--------------------
Backfills mrp and discount_pct into the products table from the raw JSON files.
Matches on product_name (exact) + source.

Run from MarketPulse-main/:  python backfill_discount.py
"""
import json
import math
import sqlite3
from pathlib import Path

ROOT    = Path(__file__).parent
DB      = ROOT / "data" / "price_comparison.db"
RAW_DIR = ROOT / "data" / "raw"

def safe(val):
    if val is None:
        return None
    try:
        v = float(val)
        return None if (math.isnan(v) or math.isinf(v)) else v
    except (TypeError, ValueError):
        return None

# ── Load all raw records into a lookup dict keyed by (source, product_name) ──
raw_lookup: dict[tuple, dict] = {}
for jf in RAW_DIR.glob("*.json"):
    records = json.loads(jf.read_text(encoding="utf-8"))
    for r in records:
        name = (r.get("product_name") or "").strip()
        src  = (r.get("source") or "").strip().lower()
        if name and src:
            raw_lookup[(src, name)] = r

print(f"Loaded {len(raw_lookup)} raw records from {RAW_DIR}")

conn = sqlite3.connect(DB)
cur  = conn.cursor()

# Fetch all products that still have NULL mrp
rows = cur.execute(
    "SELECT product_id, source, product_name FROM products WHERE mrp IS NULL OR discount_pct IS NULL"
).fetchall()
print(f"Products needing backfill: {len(rows)}")

updated = 0
for pid, source, pname in rows:
    key = (source.lower(), pname.strip())
    raw = raw_lookup.get(key)
    if not raw:
        continue
    mrp  = safe(raw.get("mrp"))
    disc = safe(raw.get("discount_pct"))
    # Compute discount if missing but mrp present
    if disc is None and mrp and mrp > 0:
        price = safe(raw.get("current_price"))
        if price:
            disc = round((mrp - price) / mrp * 100, 1)
    if mrp is None and disc is None:
        continue
    cur.execute(
        "UPDATE products SET mrp=?, discount_pct=? WHERE product_id=?",
        (mrp, disc, pid)
    )
    updated += 1

conn.commit()

# Report
total = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
with_disc = cur.execute(
    "SELECT COUNT(*) FROM products WHERE discount_pct IS NOT NULL AND discount_pct > 0"
).fetchone()[0]
print(f"Updated : {updated} rows")
print(f"Products with discount_pct > 0 : {with_disc} / {total}")

conn.close()
print("Done.")
