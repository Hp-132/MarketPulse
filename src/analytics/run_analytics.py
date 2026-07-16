"""
run_analytics.py
----------------
Runs all seven analytics functions against data/price_comparison.db,
saves every returned DataFrame to data/analytics/*.csv, and prints
a clean master summary to the terminal.

Usage (from project root):
    python src/analytics/run_analytics.py
"""

import os
import sys

# ── path setup: allow running from project root without installing as a package
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pandas as pd

from src.analytics.analytics import (
    brand_analytics,
    cross_platform_comparison,
    discount_analytics,
    platform_summary,
    price_analytics,
    rating_analytics,
    statistical_analytics,
)

# ── constants ─────────────────────────────────────────────────────────────────
DB_PATH     = os.path.join(_ROOT, "data", "price_comparison.db")
OUTPUT_DIR  = os.path.join(_ROOT, "data", "analytics")
SEP_WIDE    = "=" * 64
SEP_NARROW  = "-" * 64


# ── helpers ───────────────────────────────────────────────────────────────────

def _save(name: str, df: pd.DataFrame) -> str:
    """Write *df* to OUTPUT_DIR/<name>.csv and return the relative path."""
    path = os.path.join(OUTPUT_DIR, f"{name}.csv")
    df.to_csv(path, index=False)
    rel = os.path.relpath(path, _ROOT)
    return rel


def _section(title: str) -> None:
    print(f"\n{SEP_WIDE}")
    print(f"  {title}")
    print(SEP_WIDE)


def _saved_line(rel_path: str, df: pd.DataFrame) -> None:
    print(f"  [saved]  {rel_path}  ({len(df)} rows)")


def _fmt_inr(value: float) -> str:
    """Format a float as ₹ with comma-separated Indian numbering."""
    try:
        return f"\u20b9{value:,.0f}"
    except (TypeError, ValueError):
        return "N/A"


def _safe_get(df: pd.DataFrame, col: str, default="N/A") -> str:
    """Return first value of *col* from a single-row DataFrame, or default."""
    if df.empty or col not in df.columns:
        return default
    v = df.iloc[0][col]
    return default if pd.isna(v) else v


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # ── pre-flight ────────────────────────────────────────────────────────────
    if not os.path.exists(DB_PATH):
        print(f"[error] Database not found: {DB_PATH}")
        print("        Run the ETL pipeline first to populate the database.")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(SEP_WIDE)
    print("  MarketPulse Analytics Run")
    print(SEP_WIDE)
    print(f"  DB     : {os.path.relpath(DB_PATH, _ROOT)}")
    print(f"  Output : {os.path.relpath(OUTPUT_DIR, _ROOT)}")

    saved_files: list[str] = []

    # ── 1. platform_summary ───────────────────────────────────────────────────
    _section("1 / 6  Platform Summary")
    ps = platform_summary(DB_PATH)
    summary_df = ps["summary"]

    rel = _save("platform_summary", summary_df)
    saved_files.append(rel)
    _saved_line(rel, summary_df)

    # ── 2. price_analytics ────────────────────────────────────────────────────
    _section("2 / 6  Price Analytics")
    pa = price_analytics(DB_PATH)

    for key, df in pa.items():
        rel = _save(f"price_{key}", df)
        saved_files.append(rel)
        _saved_line(rel, df)

    # ── 3. discount_analytics ─────────────────────────────────────────────────
    _section("3 / 6  Discount Analytics")
    da = discount_analytics(DB_PATH)

    for key, df in da.items():
        rel = _save(f"discount_{key}", df)
        saved_files.append(rel)
        _saved_line(rel, df)

    # ── 4. brand_analytics ────────────────────────────────────────────────────
    _section("4 / 6  Brand Analytics")
    ba = brand_analytics(DB_PATH)

    for key, df in ba.items():
        rel = _save(f"brand_{key}", df)
        saved_files.append(rel)
        _saved_line(rel, df)

    # ── 5. rating_analytics ───────────────────────────────────────────────────
    _section("5 / 6  Rating Analytics")
    ra = rating_analytics(DB_PATH)

    for key, df in ra.items():
        rel = _save(f"rating_{key}", df)
        saved_files.append(rel)
        _saved_line(rel, df)

    # ── 6. cross_platform_comparison ──────────────────────────────────────────
    _section("6 / 6  Cross-Platform Comparison")
    cc = cross_platform_comparison(DB_PATH)

    for key, df in cc.items():
        rel = _save(f"cross_{key}", df)
        saved_files.append(rel)
        _saved_line(rel, df)

    # ── 7. statistical_analytics ──────────────────────────────────────────────
    _section("7 / 7  Statistical Analytics (volatility, correlation, outliers)")
    sa = statistical_analytics(DB_PATH)

    for key, df in sa.items():
        rel = _save(f"stats_{key}", df)
        saved_files.append(rel)
        _saved_line(rel, df)

    # ══════════════════════════════════════════════════════════════════════════
    # MASTER SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    print(f"\n{SEP_WIDE}")
    print("  MASTER SUMMARY")
    print(SEP_WIDE)

    # ── (a) Total products per source ─────────────────────────────────────────
    print("\n  TOTAL PRODUCTS PER PLATFORM")
    print(f"  {SEP_NARROW}")
    if not summary_df.empty:
        col_w = 12
        print(f"  {'Platform':<{col_w}} {'Products':>9}  {'Avg Price':>12}  "
              f"{'Avg Rating':>10}  {'Categories':>10}")
        print(f"  {'-'*col_w}  {'-'*8}  {'-'*11}  {'-'*9}  {'-'*9}")
        for _, row in summary_df.iterrows():
            avg_p = _fmt_inr(row.get("avg_price", float("nan")))
            avg_r = row.get("avg_rating", float("nan"))
            avg_r_str = f"{avg_r:.2f}" if pd.notna(avg_r) else "N/A"
            cats  = int(row.get("categories_covered", 0))
            print(f"  {str(row['source']).capitalize():<{col_w}} "
                  f"{int(row['total_products']):>9}  "
                  f"{avg_p:>12}  "
                  f"{avg_r_str:>10}  "
                  f"{cats:>10}")
    else:
        print("  No platform data available.")

    # ── (b) Avg price per category ────────────────────────────────────────────
    print(f"\n  AVG PRICE PER CATEGORY")
    print(f"  {SEP_NARROW}")
    price_cat_df = pa.get("by_category", pd.DataFrame())
    if not price_cat_df.empty:
        print(f"  {'Category':<22} {'Avg Price':>12}  {'Min':>10}  {'Max':>10}  {'# Products':>10}")
        print(f"  {'-'*22}  {'-'*11}  {'-'*9}  {'-'*9}  {'-'*9}")
        for _, row in price_cat_df.sort_values("avg_price", ascending=False).iterrows():
            print(
                f"  {str(row['category']):<22} "
                f"{_fmt_inr(row['avg_price']):>12}  "
                f"{_fmt_inr(row['min_price']):>10}  "
                f"{_fmt_inr(row['max_price']):>10}  "
                f"{int(row['product_count']):>10}"
            )
    else:
        print("  No price data available.")

    # ── (c) Top 5 most discounted products ────────────────────────────────────
    print(f"\n  TOP 5 MOST DISCOUNTED PRODUCTS")
    print(f"  {SEP_NARROW}")
    top_disc = da.get("top_20_discounted", pd.DataFrame())
    if not top_disc.empty:
        top5 = top_disc.head(5)
        print(f"  {'#':<3} {'Product':<38} {'Brand':<14} {'Platform':<10} {'Discount':>8}")
        print(f"  {'-'*3}  {'-'*37}  {'-'*13}  {'-'*9}  {'-'*7}")
        for rank, (_, row) in enumerate(top5.iterrows(), start=1):
            name  = str(row.get("product_name", ""))[:37]
            brand = str(row.get("brand", "N/A"))[:13]
            src   = str(row.get("source", "")).capitalize()[:9]
            disc  = row.get("discount_pct", float("nan"))
            disc_str = f"{disc:.1f}%" if pd.notna(disc) else "N/A"
            print(f"  {rank:<3}  {name:<38} {brand:<14} {src:<10} {disc_str:>8}")
    else:
        print("  No discount data available.")
        print("  (Discount is estimated from price_history. Products need")
        print("   >1 price_history entry to appear here.)")

    # ── (d) Which platform is cheaper per category ───────────────────────────
    print(f"\n  CHEAPER PLATFORM PER CATEGORY  (from matched pairs)")
    print(f"  {SEP_NARROW}")
    cbc = cc.get("cheaper_by_category", pd.DataFrame())
    if not cbc.empty:
        print(f"  {'Category':<22} {'Amazon cheaper':>14}  {'Flipkart cheaper':>16}  "
              f"{'Equal':>5}  {'Avg diff':>10}  {'Pairs':>5}")
        print(f"  {'-'*22}  {'-'*13}  {'-'*15}  {'-'*4}  {'-'*9}  {'-'*4}")
        for _, row in cbc.iterrows():
            amz   = int(row.get("amazon_cheaper_count",   0))
            fkrt  = int(row.get("flipkart_cheaper_count", 0))
            eq    = int(row.get("equal_price_count",      0))
            diff  = row.get("avg_price_diff_inr", float("nan"))
            diff_str = _fmt_inr(diff) if pd.notna(diff) else "N/A"
            pairs = int(row.get("total_pairs", 0))
            winner = "Amazon" if amz > fkrt else ("Flipkart" if fkrt > amz else "Equal")
            print(
                f"  {str(row['category']):<22} "
                f"{amz:>14}  "
                f"{fkrt:>16}  "
                f"{eq:>5}  "
                f"{diff_str:>10}  "
                f"{pairs:>5}  → {winner}"
            )
    else:
        print("  No matched pairs available.")
        print("  (Run src/matching/run_matching.py first to populate product_matches.)")

    # ── (e) Avg rating per category ───────────────────────────────────────────
    print(f"\n  AVG RATING PER CATEGORY")
    print(f"  {SEP_NARROW}")
    rating_cat_df = ra.get("by_category", pd.DataFrame())
    if not rating_cat_df.empty:
        print(f"  {'Category':<22} {'Avg Rating':>10}  {'Rated > 4.0':>11}  {'# Products':>10}")
        print(f"  {'-'*22}  {'-'*9}  {'-'*10}  {'-'*9}")
        for _, row in rating_cat_df.iterrows():
            avg_r = row.get("avg_rating", float("nan"))
            avg_r_str = f"{avg_r:.2f}" if pd.notna(avg_r) else "N/A"
            pct   = row.get("rated_above_4_pct", float("nan"))
            pct_str = f"{pct:.1f}%" if pd.notna(pct) else "N/A"
            print(
                f"  {str(row['category']):<22} "
                f"{avg_r_str:>10}  "
                f"{pct_str:>11}  "
                f"{int(row['product_count']):>10}"
            )
    else:
        print("  No rating data available.")

    # ── CSV file manifest ─────────────────────────────────────────────────────
    print(f"\n  CSVs SAVED  ({len(saved_files)} files  →  "
          f"{os.path.relpath(OUTPUT_DIR, _ROOT)})")
    print(f"  {SEP_NARROW}")
    for f in saved_files:
        print(f"  {f}")

    print(f"\n{SEP_WIDE}")
    print("  Done.")
    print(SEP_WIDE)


if __name__ == "__main__":
    main()
