"""
migrate_db.py — adds mrp and discount_pct columns to products table.
Run once from MarketPulse-main/:  python migrate_db.py
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "data" / "price_comparison.db"

conn = sqlite3.connect(DB)
cols = [r[1] for r in conn.execute("PRAGMA table_info(products)").fetchall()]
print("Columns before:", cols)

added = []
if "mrp" not in cols:
    conn.execute("ALTER TABLE products ADD COLUMN mrp REAL")
    added.append("mrp")
if "discount_pct" not in cols:
    conn.execute("ALTER TABLE products ADD COLUMN discount_pct REAL")
    added.append("discount_pct")

conn.commit()
cols2 = [r[1] for r in conn.execute("PRAGMA table_info(products)").fetchall()]
print("Columns after: ", cols2)
print("Added:", added if added else "nothing (already present)")
conn.close()
