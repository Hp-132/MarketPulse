"""
export_data.py
--------------
Reads the MarketPulse SQLite DB and analytics CSVs, then writes
frontend_data.json shaped to match every mock array in App.tsx.

Run from the MarketPulse-main/ directory:
    python export_data.py
"""

import json
import math
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).parent
DB_PATH   = ROOT / "data" / "price_comparison.db"
CSV_DIR   = ROOT / "data" / "analytics"
OUT_FILE  = ROOT / "frontend_data.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def read_csv(name: str) -> pd.DataFrame:
    p = CSV_DIR / name
    if not p.exists():
        print(f"  [warn] {name} not found — using empty DataFrame")
        return pd.DataFrame()
    return pd.read_csv(p)


def _conn() -> sqlite3.Connection:
    if not DB_PATH.exists():
        print(f"[error] DB not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _q(conn: sqlite3.Connection, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn)


def clean(val):
    """Replace NaN / Inf / numpy types with JSON-safe Python scalars."""
    # Handle numpy floats and ints
    try:
        import numpy as np
        if isinstance(val, (np.floating, np.integer)):
            val = val.item()
        if isinstance(val, np.bool_):
            return bool(val)
    except ImportError:
        pass
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val


def rows(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to list[dict] with NaN scrubbed."""
    # Fill NaN before converting so pandas NaN becomes None
    df = df.where(pd.notnull(df), None)
    return [
        {k: clean(v) for k, v in record.items()}
        for record in df.to_dict(orient="records")
    ]


# ── 1. KPIs  (matches KPI_DATA shape: label, value, delta, up, spark) ─────────

def build_kpis(conn: sqlite3.Connection) -> list[dict]:
    ps = read_csv("platform_summary.csv")
    total_products = int(ps["total_products"].sum()) if not ps.empty else 0

    rb = read_csv("rating_by_category.csv")
    avg_rating = round(rb["avg_rating"].mean(), 2) if not rb.empty else 0.0

    mp = read_csv("cross_matched_pairs.csv")
    matched_pairs = len(mp) if not mp.empty else 0

    bc = read_csv("brand_brand_counts.csv").dropna(subset=["brand"])
    brand_count = len(bc) if not bc.empty else 0

    pb = read_csv("price_by_category.csv")
    avg_price = round(pb["avg_price"].mean(), 0) if not pb.empty else 0.0

    def spark(base: float, length: int = 14) -> list[dict]:
        import math as m
        return [
            {"v": round(base + m.sin(i * 0.9 + 1.2) * base * 0.07 + (i / length) * base * 0.05, 2)}
            for i in range(length)
        ]

    return [
        {"label": "Products Tracked", "value": f"{total_products:,}",
         "delta": "+0", "up": True,  "spark": spark(total_products or 1)},
        {"label": "Avg. Price",       "value": f"₹{int(avg_price):,}",
         "delta": "—",  "up": True,  "spark": spark(avg_price or 1)},
        {"label": "Avg. Rating",      "value": f"{avg_rating}★",
         "delta": "+0.00", "up": True,  "spark": spark(avg_rating or 1, 14)},
        {"label": "Matched Pairs",    "value": f"{matched_pairs:,}",
         "delta": "+0", "up": True,  "spark": spark(matched_pairs or 1)},
        {"label": "Brands",           "value": f"{brand_count:,}",
         "delta": "+0", "up": True,  "spark": spark(brand_count or 1)},
    ]


# ── 2. priceByCat  (cat, budget, mid, premium) ────────────────────────────────

def build_price_by_cat() -> list[dict]:
    pl = read_csv("price_price_labels.csv")
    if pl.empty:
        return []
    pivot = (
        pl.groupby(["category", "price_label"])["current_price"]
        .mean().round(0).astype(int)
        .unstack(fill_value=0)
        .reset_index()
    )
    for col in ("budget", "mid-range", "premium"):
        if col not in pivot.columns:
            pivot[col] = 0
    pivot = pivot.rename(columns={"mid-range": "mid"})
    pivot["cat"] = pivot["category"].str.replace("_", " ").str.title()
    return rows(pivot[["cat", "budget", "mid", "premium"]])


# ── 3. discByCat  (cat, avg) ──────────────────────────────────────────────────

def build_disc_by_cat() -> list[dict]:
    dc = read_csv("discount_by_category.csv")
    if dc.empty:
        return []
    dc["cat"] = dc["category"].str.replace("_", " ").str.title()
    dc["avg"] = dc["avg_discount_pct"].round(1)
    return rows(dc[["cat", "avg"]])


# ── 4. discByBrand  (brand, avg) ──────────────────────────────────────────────

def build_disc_by_brand() -> list[dict]:
    db = read_csv("discount_by_brand.csv")
    if db.empty:
        return []
    db["avg"] = db["avg_discount_pct"].round(1)
    return rows(db[["brand", "avg"]].head(10))


# ── 5. top20  (rank, name, cat, brand, mrp, price, disc) ─────────────────────

def build_top20() -> list[dict]:
    t20 = read_csv("discount_top_20_discounted.csv")
    if t20.empty:
        return []
    t20 = t20.reset_index(drop=True)
    t20["rank"]  = range(1, len(t20) + 1)
    t20["cat"]   = t20["category"].str.replace("_", " ").str.title()
    # support both old column name (reference_price) and new (mrp)
    mrp_col      = "mrp" if "mrp" in t20.columns else "reference_price"
    t20["mrp"]   = t20[mrp_col].fillna(0).round(0).astype(int)
    t20["price"] = t20["current_price"].fillna(0).round(0).astype(int)
    t20["disc"]  = t20["discount_pct"].round(1)
    return rows(t20[["rank", "product_name", "cat", "brand", "mrp", "price", "disc"]].rename(columns={"product_name": "name"}).head(20))


# ── 6. matchedPairs  (id, name, cat, brand, amazon, flipkart, diff, cheaper) ──

def build_matched_pairs() -> list[dict]:
    mp = read_csv("cross_matched_pairs.csv")
    if mp.empty:
        return []
    mp["id"] = "MP" + (mp.index + 1).astype(str).str.zfill(3)
    mp["name"] = mp["amazon_name"]
    mp["cat"] = mp["category"].str.replace("_", " ").str.title()
    mp["brand"] = mp["amazon_brand"]
    mp["amazon"] = mp["amazon_price"].round(0).fillna(0).astype(int)
    mp["flipkart"] = mp["flipkart_price"].round(0).fillna(0).astype(int)
    mp["diff"] = mp["price_diff_inr"].abs().round(0).fillna(0).astype(int)
    mp["cheaper"] = mp["cheaper_platform"].str.capitalize()
    return rows(mp[["id", "name", "cat", "brand", "amazon", "flipkart", "diff", "cheaper"]])


# ── 7. platComp  (cat, amazon, flipkart) ──────────────────────────────────────

def build_plat_comp() -> list[dict]:
    conn = _conn()
    try:
        df = _q(
            conn,
            """
            SELECT category,
                   source,
                   AVG(current_price) AS avg_price
            FROM products
            WHERE current_price IS NOT NULL
            GROUP BY category, source
            """
        )
    finally:
        conn.close()
    if df.empty:
        return []
    pivot = df.pivot(index="category", columns="source", values="avg_price").fillna(0).round(0).astype(int).reset_index()
    for col in ("amazon", "flipkart"):
        if col not in pivot.columns:
            pivot[col] = 0
    pivot["cat"] = pivot["category"].str.replace("_", " ").str.title()
    return rows(pivot[["cat", "amazon", "flipkart"]])


# ── 8. catCheaper  (cat, amazon, flipkart) ────────────────────────────────────

def build_cat_cheaper() -> list[dict]:
    cc = read_csv("cross_cheaper_by_category.csv")
    if cc.empty:
        return []
    total = cc["amazon_cheaper_count"] + cc["flipkart_cheaper_count"] + cc["equal_price_count"]
    cc["amazon"]   = ((cc["amazon_cheaper_count"]   / total.replace(0, 1)) * 100).round(1)
    cc["flipkart"] = ((cc["flipkart_cheaper_count"] / total.replace(0, 1)) * 100).round(1)
    cc["cat"] = cc["category"].str.replace("_", " ").str.title()
    return rows(cc[["cat", "amazon", "flipkart"]])


# ── 9. cvData  (cat, cv)  ─────────────────────────────────────────────────────

def build_cv_data() -> list[dict]:
    vc = read_csv("stats_volatility_by_category.csv")
    if vc.empty:
        return []
    vc["cat"] = vc["category"].str.replace("_", " ").str.title()
    vc["cv"]  = vc["coefficient_of_variation"].round(3)
    return rows(vc[["cat", "cv"]])


# ── 10. outliers  (name, cat, brand, price, avgCat, z) ───────────────────────

def build_outliers() -> list[dict]:
    po = read_csv("stats_price_outliers.csv")
    if po.empty:
        return []
    pb = read_csv("price_by_category.csv")
    avg_map = dict(zip(pb["category"], pb["avg_price"].round(0).astype(int))) if not pb.empty else {}
    po["name"]   = po["product_name"]
    po["cat"]    = po["category"].str.replace("_", " ").str.title()
    po["brand"]  = po["brand"].fillna("Unknown")
    po["price"]  = po["current_price"].round(0).fillna(0).astype(int)
    po["avgCat"] = po["category"].map(avg_map).fillna(0).astype(int)
    po["z"]      = po["price_zscore"].abs().round(2)
    return rows(po[["name", "cat", "brand", "price", "avgCat", "z"]].head(20))


# ── 11. sentDonut  (label, value, color) ─────────────────────────────────────

SENT_COLORS = {
    "positive": "#6EC6CA",
    "neutral":  "#8474A1",
    "critical": "#CCA8D8",
    "poor":     "#055B5C",
}

def build_sent_donut() -> list[dict]:
    rb = read_csv("rating_by_category.csv")
    if rb.empty:
        return []
    total = rb["product_count"].sum()
    pos   = (rb["product_count"] * rb["rated_above_4_pct"] / 100).sum()
    poor  = (rb["product_count"] * (rb["avg_rating"] < 2).astype(int)).sum()
    neu_raw  = rb[rb["avg_rating"].between(3, 3.9)]["product_count"].sum()
    crit_raw = rb[rb["avg_rating"].between(2, 2.9)]["product_count"].sum()
    pos_pct  = round(pos  / total * 100, 1) if total else 0
    poor_pct = round(poor / total * 100, 1) if total else 0
    neu_pct  = round(neu_raw  / total * 100, 1) if total else 0
    crit_pct = round(crit_raw / total * 100, 1) if total else 0
    rest = round(100 - pos_pct - poor_pct - neu_pct - crit_pct, 1)
    neu_pct += rest  # absorb rounding remainder
    return [
        {"label": "Positive ≥4★",    "value": pos_pct,  "color": SENT_COLORS["positive"]},
        {"label": "Neutral 3–3.9★",  "value": neu_pct,  "color": SENT_COLORS["neutral"]},
        {"label": "Critical 2–2.9★", "value": crit_pct, "color": SENT_COLORS["critical"]},
        {"label": "Poor <2★",        "value": poor_pct, "color": SENT_COLORS["poor"]},
    ]


# ── 12. sentTable  (cat, pos, neu, crit, poor, avgRating) ────────────────────

def build_sent_table() -> list[dict]:
    rb = read_csv("rating_by_category.csv")
    if rb.empty:
        return []
    result = []
    for _, r in rb.iterrows():
        pos  = round(float(r["rated_above_4_pct"]), 1)
        poor = 0.0
        crit = round(max(0.0, (4.0 - float(r["avg_rating"])) * 10), 1)
        neu  = round(max(0.0, 100.0 - pos - crit - poor), 1)
        result.append({
            "cat":       r["category"].replace("_", " ").title(),
            "pos":       pos,
            "neu":       neu,
            "crit":      crit,
            "poor":      poor,
            "avgRating": round(float(r["avg_rating"]), 2),
        })
    return result


# ── 13. products / catalogue  (id, name, brand, cat, amazon, flipkart, rating,
#                               reviews, disc, avail) ─────────────────────────

def build_products(conn: sqlite3.Connection) -> list[dict]:
    df = _q(
        conn,
        """
        SELECT p.product_id, p.product_name AS name, p.brand, p.category,
               p.source, p.current_price,
               r.rating, r.review_count
        FROM products p
        LEFT JOIN reviews r ON r.product_id = p.product_id
        WHERE p.current_price IS NOT NULL
        ORDER BY r.rating DESC NULLS LAST
        """
    )
    if df.empty:
        return []

    amz = df[df["source"] == "amazon"].set_index("product_name" if "product_name" in df.columns else "name")
    fk  = df[df["source"] == "flipkart"]

    # Build per-product rows grouping by name
    grouped = df.groupby("name")
    out = []
    idx = 1
    for name, grp in grouped:
        amz_row = grp[grp["source"] == "amazon"].iloc[0] if not grp[grp["source"] == "amazon"].empty else None
        fk_row  = grp[grp["source"] == "flipkart"].iloc[0] if not grp[grp["source"] == "flipkart"].empty else None
        row = grp.iloc[0]
        amazon_price   = int(amz_row["current_price"]) if amz_row is not None else None
        flipkart_price = int(fk_row["current_price"])  if fk_row  is not None else None
        avail = "both" if (amz_row is not None and fk_row is not None) else \
                ("amazon" if amz_row is not None else "flipkart")
        out.append({
            "id":       f"P{idx:03d}",
            "name":     str(name)[:80],
            "brand":    str(row["brand"]) if row["brand"] else "Unknown",
            "cat":      str(row["category"]).replace("_", " ").title(),
            "amazon":   amazon_price,
            "flipkart": flipkart_price,
            "rating":   round(float(row["rating"]), 1) if (row["rating"] is not None and not (isinstance(row["rating"], float) and math.isnan(row["rating"]))) else None,
            "reviews":  int(row["review_count"]) if (row["review_count"] is not None and not (isinstance(row["review_count"], float) and math.isnan(row["review_count"]))) else 0,
            "disc":     0.0,
            "avail":    avail,
        })
        idx += 1
    return out[:100]  # cap at 100 for performance


# ── 14. brandPanel  (brand, count, avail) ────────────────────────────────────

def build_brand_panel() -> list[dict]:
    bc = read_csv("brand_brand_counts.csv").dropna(subset=["brand"])
    if bc.empty:
        return []
    bc["avail"] = bc["platform_presence"]
    bc["count"] = bc["product_count"].astype(int)
    return rows(bc[["brand", "count", "avail"]].head(20))


# ── 15. pipeline_health  (last_updated, sources, etl_runs) ───────────────────

def build_pipeline_health(conn: sqlite3.Connection) -> dict:
    from datetime import datetime

    # Most recent run_timestamp — use the single latest run across all sources
    # (etl_run_log.source may be 'combined', 'amazon', 'flipkart', etc.)
    recent_df = _q(
        conn,
        """
        SELECT source, MAX(run_timestamp) AS last_scraped
        FROM etl_run_log
        GROUP BY source
        """
    )
    recent_map: dict = {}
    global_latest: str = datetime.now().isoformat()
    if not recent_df.empty:
        for _, row in recent_df.iterrows():
            key = str(row["source"]).lower()
            recent_map[key] = str(row["last_scraped"])
        # Use the most recent timestamp across all sources as the global fallback
        global_latest = max(recent_map.values())

    def _latest_for(key: str) -> str:
        """Return per-platform timestamp if available, else the global latest."""
        return recent_map.get(key, global_latest)

    # Products count per source
    count_df = _q(conn, "SELECT source, COUNT(*) AS cnt FROM products GROUP BY source")
    count_map: dict = {}
    if not count_df.empty:
        for _, row in count_df.iterrows():
            count_map[str(row["source"]).lower()] = int(row["cnt"])

    sources = []
    for platform, key in [("Amazon", "amazon"), ("Flipkart", "flipkart")]:
        sources.append({
            "platform":         platform,
            "status":           "healthy",
            "last_scraped":     _latest_for(key),
            "products_indexed": count_map.get(key, 0),
        })

    # Last 10 ETL runs
    runs_df = _q(
        conn,
        """
        SELECT run_id, run_timestamp, records_processed,
               0 AS rows_inserted,
               duplicates_removed,
               0 AS errors
        FROM etl_run_log
        ORDER BY run_id DESC
        LIMIT 10
        """
    )
    etl_runs = []
    if not runs_df.empty:
        for _, row in runs_df.iterrows():
            etl_runs.append({
                "run_id":             int(row["run_id"]),
                "run_timestamp":      str(row["run_timestamp"]),
                "records_processed":  int(row["records_processed"]) if row["records_processed"] else 0,
                "rows_inserted":      int(row["rows_inserted"])      if row["rows_inserted"]      else 0,
                "duplicates_removed": int(row["duplicates_removed"]) if row["duplicates_removed"] else 0,
                "errors":             int(row["errors"])              if row["errors"]              else 0,
            })

    return {
        "last_updated": datetime.now().isoformat(),
        "sources":      sources,
        "etl_runs":     etl_runs,
    }


# ── 16-old. pipelineLogs  (id, ts, platform, cat, status, count, dur, note) ──

def build_pipeline_logs(conn: sqlite3.Connection) -> list[dict]:
    df = _q(conn, "SELECT * FROM etl_run_log ORDER BY run_id DESC LIMIT 20")
    if df.empty:
        return []
    out = []
    for _, r in df.iterrows():
        out.append({
            "id":       int(r["run_id"]),
            "ts":       str(r["run_timestamp"])[:19].replace("T", " "),
            "platform": str(r["source"]).capitalize(),
            "cat":      "All Categories",
            "status":   str(r["status"]).lower(),
            "count":    int(r["records_processed"]) if r["records_processed"] else 0,
            "dur":      "—",
            "note":     None,
        })
    return out


# ── 16. platformSummary  (platform, products, brands, cats, lastRun, status,
#                          health) ─────────────────────────────────────────────

def build_platform_summary() -> list[dict]:
    ps = read_csv("platform_summary.csv")
    if ps.empty:
        return []
    out = []
    for _, r in ps.iterrows():
        out.append({
            "platform": str(r["source"]).capitalize(),
            "products": int(r["total_products"]),
            "brands":   int(r["brands_covered"]),
            "cats":     int(r["categories_covered"]),
            "lastRun":  "—",
            "status":   "healthy",
            "health":   min(100.0, round(float(r["avg_rating"]) / 5.0 * 100, 1)) if r["avg_rating"] else 90.0,
        })
    return out


# ── 17. scatterData  (price, rating) ─────────────────────────────────────────

def build_scatter(conn: sqlite3.Connection) -> list[dict]:
    df = _q(
        conn,
        """
        SELECT p.current_price AS price, r.rating
        FROM products p
        JOIN reviews r ON r.product_id = p.product_id
        WHERE p.current_price IS NOT NULL AND r.rating IS NOT NULL
        ORDER BY p.current_price
        """
    )
    if df.empty:
        return []
    df["price"]  = df["price"].round(0).astype(int)
    df["rating"] = df["rating"].round(1)
    return rows(df)


# ── 18. ratingByBrand  (brand, rating) ───────────────────────────────────────

def build_rating_by_brand() -> list[dict]:
    rb = read_csv("rating_by_brand.csv").dropna(subset=["brand"])
    if rb.empty:
        return []
    rb = rb[rb["product_count"] >= 3].sort_values("avg_rating", ascending=False).head(10)
    rb["rating"] = rb["avg_rating"].round(2)
    return rows(rb[["brand", "rating"]])


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("MarketPulse — exporting frontend_data.json")
    print(f"  DB   : {DB_PATH}")
    print(f"  CSVs : {CSV_DIR}")
    print(f"  Out  : {OUT_FILE}\n")

    conn = _conn()
    try:
        # pearson correlation
        corr_df = read_csv("stats_price_rating_correlation.csv")
        pearson_r = float(corr_df["pearson_r"].iloc[0]) if not corr_df.empty and "pearson_r" in corr_df.columns else 0.155

        payload = {
            "kpis":            build_kpis(conn),
            "priceByCat":      build_price_by_cat(),
            "discByCat":       build_disc_by_cat(),
            "discByBrand":     build_disc_by_brand(),
            "top20":           build_top20(),
            "matchedPairs":    build_matched_pairs(),
            "platComp":        build_plat_comp(),
            "catCheaper":      build_cat_cheaper(),
            "cvData":          build_cv_data(),
            "outliers":        build_outliers(),
            "sentDonut":       build_sent_donut(),
            "sentTable":       build_sent_table(),
            "products":        build_products(conn),
            "brandPanel":      build_brand_panel(),
            "pipelineLogs":    build_pipeline_logs(conn),
            "platformSummary": build_platform_summary(),
            "scatterData":     build_scatter(conn),
            "pearsonR":        pearson_r,
            "pipeline_health": build_pipeline_health(conn),
        }
    finally:
        conn.close()

    OUT_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")

    # Auto-copy to all frontend public/ folders
    import shutil
    for frontend_name in ("Professional Dark-Theme Dashboard", "frontend"):
        public_dir = ROOT / frontend_name / "public"
        if public_dir.exists():
            dest = public_dir / "frontend_data.json"
            shutil.copy(OUT_FILE, dest)
            print(f"Copied → {dest}")

    print("Done. Counts:")
    for k, v in payload.items():
        if isinstance(v, list):
            print(f"  {k:<18} {len(v)} rows")
        else:
            print(f"  {k:<18} {v}")
    print(f"\nWrote {OUT_FILE.stat().st_size // 1024} KB → {OUT_FILE}")


if __name__ == "__main__":
    main()
