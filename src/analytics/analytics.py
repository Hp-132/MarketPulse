"""
analytics.py
------------
Six analytics functions over the MarketPulse SQLite database.
Every function accepts a *db_path* string, queries with sqlite3 + pandas,
and returns a dict of named DataFrames.

Functions
---------
price_analytics          -- avg/min/max per category & brand; budget/mid/premium labels
discount_analytics       -- avg discount per category & brand; top-20 most discounted
brand_analytics          -- product count per brand; single-platform vs both-platform flag
rating_analytics         -- avg rating per category & brand; % rated > 4.0 per category
platform_summary         -- totals & averages grouped by source
cross_platform_comparison -- price delta (₹ and %) per matched pair; cheaper platform per category
statistical_analytics    -- price volatility (std dev) per category/brand; price-rating
                            correlation; z-score based price outlier flags

NOTE on discount_pct
--------------------
The raw scraper captures mrp + discount_pct, but the current ETL pipeline
does NOT persist those columns to the database — only current_price is
stored in products and price_history.  discount_analytics therefore derives
a *price-drop estimate* from price_history: the earliest recorded price for
each product is treated as the reference (MRP proxy) and the latest is
treated as the current price.  Products with only one price_history row
(no history of price movement) are excluded from discount calculations
because no reference price is available for comparison.
"""

import sqlite3

import pandas as pd

# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _connect(db_path: str) -> sqlite3.Connection:
    """Open a read-only-friendly connection with row_factory set."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _query(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> pd.DataFrame:
    """Execute *sql* and return a DataFrame."""
    return pd.read_sql_query(sql, conn, params=params)


# ---------------------------------------------------------------------------
# 1. price_analytics
# ---------------------------------------------------------------------------

def price_analytics(db_path: str) -> dict[str, pd.DataFrame]:
    """
    Returns
    -------
    "by_category" : avg_price, min_price, max_price, product_count — one row per category
    "by_brand"    : avg_price, min_price, max_price, product_count — one row per brand
    "price_labels": every product with its price_label
                    (budget / mid-range / premium) based on within-category terciles
    """
    conn = _connect(db_path)
    try:
        products = _query(
            conn,
            """
            SELECT product_id, source, product_name, brand, category, current_price
            FROM   products
            WHERE  current_price IS NOT NULL AND current_price > 0
            """,
        )
    finally:
        conn.close()

    if products.empty:
        empty = pd.DataFrame()
        return {"by_category": empty, "by_brand": empty, "price_labels": empty}

    # ── by category ──────────────────────────────────────────────────────────
    by_category = (
        products.groupby("category", dropna=False)["current_price"]
        .agg(avg_price="mean", min_price="min", max_price="max", product_count="count")
        .round(2)
        .reset_index()
    )

    # ── by brand ─────────────────────────────────────────────────────────────
    by_brand = (
        products.groupby("brand", dropna=False)["current_price"]
        .agg(avg_price="mean", min_price="min", max_price="max", product_count="count")
        .round(2)
        .reset_index()
    )

    # ── price labels via within-category terciles ─────────────────────────────
    def _label_tercile(series: pd.Series) -> pd.Series:
        """Assign budget/mid-range/premium based on 33rd and 66th percentile."""
        if series.nunique() < 2:
            # Not enough variation to split into three bands
            return pd.Series("mid-range", index=series.index)
        t33 = series.quantile(1 / 3)
        t66 = series.quantile(2 / 3)
        return series.apply(
            lambda p: "budget" if p <= t33 else ("premium" if p > t66 else "mid-range")
        )

    products = products.copy()
    products["price_label"] = (
        products.groupby("category", group_keys=False)["current_price"]
        .apply(_label_tercile)
    )

    price_labels = products[
        ["product_id", "source", "product_name", "brand", "category",
         "current_price", "price_label"]
    ].reset_index(drop=True)

    return {
        "by_category": by_category,
        "by_brand":    by_brand,
        "price_labels": price_labels,
    }


# ---------------------------------------------------------------------------
# 2. discount_analytics
# ---------------------------------------------------------------------------

def discount_analytics(db_path: str) -> dict[str, pd.DataFrame]:
    """
    Discount is read directly from products.mrp and products.discount_pct,
    which are populated by the ETL pipeline from the scraper output.
    Falls back to computing (mrp - current_price) / mrp * 100 when
    discount_pct is NULL but mrp is present.

    Returns
    -------
    "by_category"       : avg_discount_pct per category
    "by_brand"          : avg_discount_pct per brand
    "top_20_discounted" : top 20 products by discount_pct
    """
    conn = _connect(db_path)
    try:
        products = _query(
            conn,
            """
            SELECT product_id, product_name, brand, category, source,
                   current_price, mrp, discount_pct
            FROM   products
            WHERE  current_price IS NOT NULL AND current_price > 0
            """,
        )
    finally:
        conn.close()

    empty_cols_cat  = ["category", "avg_discount_pct", "product_count"]
    empty_cols_brand = ["brand", "avg_discount_pct", "product_count"]
    empty_cols_top  = ["product_id", "product_name", "brand", "category",
                       "source", "mrp", "current_price", "discount_pct"]

    if products.empty:
        return {
            "by_category":       pd.DataFrame(columns=empty_cols_cat),
            "by_brand":          pd.DataFrame(columns=empty_cols_brand),
            "top_20_discounted": pd.DataFrame(columns=empty_cols_top),
        }

    df = products.copy()

    # Fill missing discount_pct from mrp when possible
    mask_missing = df["discount_pct"].isna() & df["mrp"].notna() & (df["mrp"] > 0)
    df.loc[mask_missing, "discount_pct"] = (
        (df.loc[mask_missing, "mrp"] - df.loc[mask_missing, "current_price"])
        / df.loc[mask_missing, "mrp"] * 100
    ).round(2)

    # Keep only rows with a valid positive discount
    df = df[df["discount_pct"].notna() & (df["discount_pct"] > 0)]

    if df.empty:
        return {
            "by_category":       pd.DataFrame(columns=empty_cols_cat),
            "by_brand":          pd.DataFrame(columns=empty_cols_brand),
            "top_20_discounted": pd.DataFrame(columns=empty_cols_top),
        }

    # ── by category ──────────────────────────────────────────────────────────
    by_category = (
        df.groupby("category", dropna=False)["discount_pct"]
        .agg(avg_discount_pct="mean", product_count="count")
        .round(2)
        .reset_index()
        .sort_values("avg_discount_pct", ascending=False)
    )

    # ── by brand ─────────────────────────────────────────────────────────────
    by_brand = (
        df.groupby("brand", dropna=False)["discount_pct"]
        .agg(avg_discount_pct="mean", product_count="count")
        .round(2)
        .reset_index()
        .sort_values("avg_discount_pct", ascending=False)
    )

    # ── top 20 most discounted ────────────────────────────────────────────────
    top_20 = (
        df[["product_id", "product_name", "brand", "category", "source",
            "mrp", "current_price", "discount_pct"]]
        .sort_values("discount_pct", ascending=False)
        .head(20)
        .reset_index(drop=True)
    )

    return {
        "by_category":       by_category,
        "by_brand":          by_brand,
        "top_20_discounted": top_20,
    }


# ---------------------------------------------------------------------------
# 3. brand_analytics
# ---------------------------------------------------------------------------

def brand_analytics(db_path: str) -> dict[str, pd.DataFrame]:
    """
    Returns
    -------
    "brand_counts"   : product_count, amazon_count, flipkart_count per brand,
                       plus a 'platform_presence' column:
                         'both'     — brand appears on Amazon AND Flipkart
                         'amazon'   — Amazon only
                         'flipkart' — Flipkart only
    """
    conn = _connect(db_path)
    try:
        products = _query(
            conn,
            "SELECT product_id, brand, source FROM products",
        )
    finally:
        conn.close()

    if products.empty:
        return {"brand_counts": pd.DataFrame()}

    # Total count per brand
    total = (
        products.groupby("brand", dropna=False)
        .size()
        .rename("product_count")
        .reset_index()
    )

    # Per-platform counts — pivot
    platform_pivot = (
        products.assign(source=products["source"].str.lower())
        .groupby(["brand", "source"], dropna=False)
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    # Ensure both columns always exist even if one platform has no products
    for col in ("amazon", "flipkart"):
        if col not in platform_pivot.columns:
            platform_pivot[col] = 0
    platform_pivot = platform_pivot.rename(
        columns={"amazon": "amazon_count", "flipkart": "flipkart_count"}
    )

    brand_counts = total.merge(platform_pivot[["brand", "amazon_count", "flipkart_count"]],
                               on="brand", how="left")
    brand_counts[["amazon_count", "flipkart_count"]] = (
        brand_counts[["amazon_count", "flipkart_count"]].fillna(0).astype(int)
    )

    def _presence(row: pd.Series) -> str:
        on_amazon   = row["amazon_count"]   > 0
        on_flipkart = row["flipkart_count"] > 0
        if on_amazon and on_flipkart:
            return "both"
        if on_amazon:
            return "amazon"
        return "flipkart"

    brand_counts["platform_presence"] = brand_counts.apply(_presence, axis=1)
    brand_counts = brand_counts.sort_values("product_count", ascending=False).reset_index(drop=True)

    return {"brand_counts": brand_counts}


# ---------------------------------------------------------------------------
# 4. rating_analytics
# ---------------------------------------------------------------------------

def rating_analytics(db_path: str) -> dict[str, pd.DataFrame]:
    """
    Returns
    -------
    "by_category"       : avg_rating, rated_above_4_pct, product_count per category
    "by_brand"          : avg_rating, product_count per brand
    """
    conn = _connect(db_path)
    try:
        df = _query(
            conn,
            """
            SELECT p.product_id,
                   p.brand,
                   p.category,
                   r.rating
            FROM   products p
            JOIN   reviews  r ON r.product_id = p.product_id
            WHERE  r.rating IS NOT NULL
            """,
        )
    finally:
        conn.close()

    if df.empty:
        empty = pd.DataFrame()
        return {"by_category": empty, "by_brand": empty}

    # ── by category ──────────────────────────────────────────────────────────
    def _above_4_pct(s: pd.Series) -> float:
        return round((s > 4.0).sum() / len(s) * 100, 2)

    by_category = (
        df.groupby("category", dropna=False)["rating"]
        .agg(
            avg_rating="mean",
            product_count="count",
            rated_above_4_pct=_above_4_pct,
        )
        .round({"avg_rating": 2})
        .reset_index()
        .sort_values("avg_rating", ascending=False)
    )

    # ── by brand ─────────────────────────────────────────────────────────────
    by_brand = (
        df.groupby("brand", dropna=False)["rating"]
        .agg(avg_rating="mean", product_count="count")
        .round(2)
        .reset_index()
        .sort_values("avg_rating", ascending=False)
    )

    return {"by_category": by_category, "by_brand": by_brand}


# ---------------------------------------------------------------------------
# 5. platform_summary
# ---------------------------------------------------------------------------

def platform_summary(db_path: str) -> dict[str, pd.DataFrame]:
    """
    Returns
    -------
    "summary" : one row per source (amazon / flipkart) with
                total_products, avg_price, avg_rating, avg_review_count,
                categories_covered, brands_covered
    """
    conn = _connect(db_path)
    try:
        df = _query(
            conn,
            """
            SELECT p.product_id,
                   p.source,
                   p.category,
                   p.brand,
                   p.current_price,
                   r.rating,
                   r.review_count
            FROM   products p
            LEFT JOIN reviews r ON r.product_id = p.product_id
            """,
        )
    finally:
        conn.close()

    if df.empty:
        return {"summary": pd.DataFrame()}

    df["source"] = df["source"].str.lower()

    agg = (
        df.groupby("source")
        .agg(
            total_products  =("product_id",    "count"),
            avg_price       =("current_price", "mean"),
            avg_rating      =("rating",        "mean"),
            avg_review_count=("review_count",  "mean"),
            categories_covered=("category",    "nunique"),
            brands_covered  =("brand",         "nunique"),
        )
        .round(2)
        .reset_index()
    )

    return {"summary": agg}


# ---------------------------------------------------------------------------
# 6. cross_platform_comparison
# ---------------------------------------------------------------------------

def cross_platform_comparison(db_path: str) -> dict[str, pd.DataFrame]:
    """
    Joins product_matches with the products table twice (aliased) to get
    Amazon and Flipkart prices side by side.

    Returns
    -------
    "matched_pairs"       : every matched pair with amazon_price, flipkart_price,
                            price_diff_inr (amazon - flipkart),
                            price_diff_pct (relative to amazon price),
                            cheaper_platform, confidence_score, category
    "cheaper_by_category" : for each category — count of pairs where amazon
                            is cheaper, where flipkart is cheaper, where they
                            are equal, and the avg price_diff_inr
    """
    conn = _connect(db_path)
    try:
        pairs = _query(
            conn,
            """
            SELECT
                pm.match_id,
                pm.confidence_score,
                pm.amazon_product_id,
                pm.flipkart_product_id,
                pa.product_name  AS amazon_name,
                pa.brand         AS amazon_brand,
                pa.category      AS category,
                pa.current_price AS amazon_price,
                pf.product_name  AS flipkart_name,
                pf.current_price AS flipkart_price
            FROM product_matches pm
            JOIN products pa ON pa.product_id = pm.amazon_product_id
            JOIN products pf ON pf.product_id = pm.flipkart_product_id
            WHERE pa.current_price IS NOT NULL
              AND pf.current_price IS NOT NULL
            """,
        )
    finally:
        conn.close()

    if pairs.empty:
        empty = pd.DataFrame()
        return {"matched_pairs": empty, "cheaper_by_category": empty}

    # ── per-pair price comparison ─────────────────────────────────────────────
    pairs = pairs.copy()
    pairs["price_diff_inr"] = (pairs["amazon_price"] - pairs["flipkart_price"]).round(2)
    pairs["price_diff_pct"] = (
        (pairs["amazon_price"] - pairs["flipkart_price"]) / pairs["amazon_price"] * 100
    ).round(2)

    def _cheaper(row: pd.Series) -> str:
        diff = row["price_diff_inr"]
        if diff > 0:
            return "flipkart"   # amazon is more expensive → flipkart is cheaper
        if diff < 0:
            return "amazon"     # amazon is cheaper
        return "equal"

    pairs["cheaper_platform"] = pairs.apply(_cheaper, axis=1)

    matched_pairs = pairs[[
        "match_id", "amazon_product_id", "flipkart_product_id",
        "amazon_name", "flipkart_name", "amazon_brand", "category",
        "amazon_price", "flipkart_price",
        "price_diff_inr", "price_diff_pct",
        "cheaper_platform", "confidence_score",
    ]].reset_index(drop=True)

    # ── cheaper platform per category ────────────────────────────────────────
    cat_grp = pairs.groupby("category", dropna=False)

    cheaper_counts = cat_grp["cheaper_platform"].value_counts().unstack(fill_value=0)
    for col in ("amazon", "flipkart", "equal"):
        if col not in cheaper_counts.columns:
            cheaper_counts[col] = 0
    cheaper_counts = cheaper_counts.rename(
        columns={
            "amazon":   "amazon_cheaper_count",
            "flipkart": "flipkart_cheaper_count",
            "equal":    "equal_price_count",
        }
    )

    avg_diff = cat_grp["price_diff_inr"].mean().round(2).rename("avg_price_diff_inr")
    total    = cat_grp.size().rename("total_pairs")

    cheaper_by_category = (
        cheaper_counts
        .join(avg_diff)
        .join(total)
        .reset_index()
        .sort_values("total_pairs", ascending=False)
    )

    return {
        "matched_pairs":       matched_pairs,
        "cheaper_by_category": cheaper_by_category,
    }


# ---------------------------------------------------------------------------
# 7. statistical_analytics
# ---------------------------------------------------------------------------

def statistical_analytics(db_path: str) -> dict[str, pd.DataFrame]:
    """
    Basic descriptive-statistics layer over products + reviews: price
    volatility, price-rating correlation, and outlier flags.

    Returns
    -------
    "volatility_by_category" : mean price, std dev, and coefficient of
                                variation (std / mean) per category
    "volatility_by_brand"    : same, grouped by brand
    "price_rating_correlation" : single-row DataFrame with the Pearson
                                correlation coefficient between
                                current_price and rating, plus sample size
    "price_outliers"        : products whose price z-score (within their
                                own category) has |z| > 2 — i.e. priced
                                unusually high or low relative to peers
    """
    conn = _connect(db_path)
    try:
        df = _query(
            conn,
            """
            SELECT p.product_id, p.source, p.product_name, p.brand,
                   p.category, p.current_price, r.rating
            FROM products p
            LEFT JOIN reviews r ON r.product_id = p.product_id
            WHERE p.current_price IS NOT NULL
            """,
        )
    finally:
        conn.close()

    if df.empty:
        empty = pd.DataFrame()
        return {
            "volatility_by_category": empty,
            "volatility_by_brand": empty,
            "price_rating_correlation": empty,
            "price_outliers": empty,
        }

    # ── volatility (std dev + coefficient of variation) ──────────────────────
    def _volatility(group_col: str) -> pd.DataFrame:
        grp = df.groupby(group_col)["current_price"]
        out = grp.agg(mean_price="mean", std_price="std", product_count="count").round(2)
        out["std_price"] = out["std_price"].fillna(0.0)
        out["coefficient_of_variation"] = (
            (out["std_price"] / out["mean_price"]).round(3)
        )
        return out.reset_index()

    volatility_by_category = _volatility("category")
    volatility_by_brand = _volatility("brand")

    # ── price-rating correlation ──────────────────────────────────────────────
    valid = df.dropna(subset=["current_price", "rating"])
    if len(valid) >= 2:
        corr = valid["current_price"].corr(valid["rating"])
        correlation_df = pd.DataFrame(
            [{
                "metric": "price_vs_rating",
                "pearson_r": round(corr, 3) if pd.notna(corr) else None,
                "n_products": len(valid),
                "note": (
                    "Small sample size — treat as directional, not "
                    "statistically conclusive." if len(valid) < 30 else ""
                ),
            }]
        )
    else:
        correlation_df = pd.DataFrame(
            [{"metric": "price_vs_rating", "pearson_r": None, "n_products": len(valid),
              "note": "Not enough paired data to compute correlation."}]
        )

    # ── outlier detection (z-score within category) ──────────────────────────
    def _zscore(group: pd.DataFrame) -> pd.Series:
        std = group["current_price"].std()
        mean = group["current_price"].mean()
        if not std or pd.isna(std):
            return pd.Series(0.0, index=group.index)
        return (group["current_price"] - mean) / std

    df = df.copy()
    df["price_zscore"] = (
        df.groupby("category", group_keys=False)[["current_price", "category"]]
        .apply(lambda g: _zscore(g))
    )
    outliers = df[df["price_zscore"].abs() > 2].copy()
    outliers["price_zscore"] = outliers["price_zscore"].round(2)
    outliers = outliers[[
        "product_id", "source", "product_name", "brand", "category",
        "current_price", "price_zscore",
    ]].sort_values("price_zscore", ascending=False).reset_index(drop=True)

    return {
        "volatility_by_category": volatility_by_category,
        "volatility_by_brand": volatility_by_brand,
        "price_rating_correlation": correlation_df,
        "price_outliers": outliers,
    }
