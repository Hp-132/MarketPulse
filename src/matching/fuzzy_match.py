"""
fuzzy_match.py
--------------
Matches Amazon products against Flipkart products within the same category
using rapidfuzz token_sort_ratio. Brand equality is enforced when both
products have a non-null brand value.

Usage (as a module):
    from src.matching.fuzzy_match import match_products
    summary, results_df = match_products("data/price_comparison.db", threshold=85)
"""

import sqlite3
import pandas as pd
from rapidfuzz import fuzz




_CREATE_PRODUCT_MATCHES = """
CREATE TABLE IF NOT EXISTS product_matches (
    match_id          INTEGER PRIMARY KEY,
    amazon_product_id INTEGER,
    flipkart_product_id INTEGER,
    confidence_score  REAL,
    FOREIGN KEY (amazon_product_id)   REFERENCES products(product_id),
    FOREIGN KEY (flipkart_product_id) REFERENCES products(product_id)
);
"""


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create product_matches if it doesn't exist, then rename ebay column if present."""
    cur = conn.cursor()

    # Create the table if it doesn't exist yet
    cur.execute(_CREATE_PRODUCT_MATCHES)
    conn.commit()

    # Check if the legacy column name exists and rename it
    cur.execute("PRAGMA table_info(product_matches)")
    columns = [row[1] for row in cur.fetchall()]
    if "ebay_product_id" in columns and "flipkart_product_id" not in columns:
        cur.execute(
            "ALTER TABLE product_matches RENAME COLUMN ebay_product_id TO flipkart_product_id"
        )
        conn.commit()
        print("[schema] Renamed ebay_product_id -> flipkart_product_id")
    elif "ebay_product_id" in columns and "flipkart_product_id" in columns:
        # Both columns exist — unusual state; just report it
        print(
            "[schema] WARNING: both ebay_product_id and flipkart_product_id exist in "
            "product_matches. Skipping rename."
        )




def _brands_compatible(brand_a: object, brand_b: object) -> bool:
    """
    Returns True when brands can be considered a match.
    - If either brand is null/empty, we cannot disqualify on brand → return True.
    - If both are non-null, they must match case-insensitively.
    """
    a_valid = brand_a and str(brand_a).strip()
    b_valid = brand_b and str(brand_b).strip()

    if not a_valid or not b_valid:
        return True  # can't compare → don't disqualify

    return str(brand_a).strip().lower() == str(brand_b).strip().lower()


def match_products(
    db_path: str,
    threshold: int = 85,
) -> tuple[dict, pd.DataFrame]:
    """
    Read products from *db_path*, find Amazon/Flipkart pairs whose
    ``product_name`` scores >= *threshold* via token_sort_ratio AND
    whose brands are compatible, then insert novel pairs into
    ``product_matches``.

    Returns
    -------
    summary : dict
        Keys: total_amazon, total_flipkart, matches_found, matches_saved
    results_df : pd.DataFrame
        All accepted matches (including those already in DB).
        Columns: amazon_product_id, flipkart_product_id, confidence_score,
                 amazon_name, flipkart_name, category
    """
    conn = sqlite3.connect(db_path)

    try:
        _ensure_schema(conn)

        
        products = pd.read_sql_query(
            "SELECT product_id, source, product_name, brand, category FROM products",
            conn,
        )

        amazon_df = products[products["source"].str.lower() == "amazon"].copy()
        flipkart_df = products[products["source"].str.lower() == "flipkart"].copy()

        # ------------------------------------------------------------------
        # Load existing pairs so we can skip duplicates
        # ------------------------------------------------------------------
        existing = pd.read_sql_query(
            "SELECT amazon_product_id, flipkart_product_id FROM product_matches",
            conn,
        )
        existing_pairs: set[tuple[int, int]] = set(
            zip(existing["amazon_product_id"], existing["flipkart_product_id"])
        )

        
        match_records: list[dict] = []

        categories = set(amazon_df["category"].dropna()) & set(
            flipkart_df["category"].dropna()
        )

        for cat in categories:
            amz_cat = amazon_df[amazon_df["category"] == cat]
            fkrt_cat = flipkart_df[flipkart_df["category"] == cat]

            for _, a_row in amz_cat.iterrows():
                a_name: str = str(a_row["product_name"])
                a_id: int = int(a_row["product_id"])
                a_brand = a_row["brand"]

                for _, f_row in fkrt_cat.iterrows():
                    f_name: str = str(f_row["product_name"])
                    f_id: int = int(f_row["product_id"])
                    f_brand = f_row["brand"]

                    # Skip if brand mismatch (when both brands are known)
                    if not _brands_compatible(a_brand, f_brand):
                        continue

                    score: float = fuzz.token_sort_ratio(a_name, f_name)

                    if score >= threshold:
                        match_records.append(
                            {
                                "amazon_product_id": a_id,
                                "flipkart_product_id": f_id,
                                "confidence_score": score,
                                "amazon_name": a_name,
                                "flipkart_name": f_name,
                                "category": cat,
                            }
                        )

        results_df = pd.DataFrame(
            match_records,
            columns=[
                "amazon_product_id",
                "flipkart_product_id",
                "confidence_score",
                "amazon_name",
                "flipkart_name",
                "category",
            ],
        )

        
        cur = conn.cursor()
        matches_saved = 0

        for _, row in results_df.iterrows():
            pair = (int(row["amazon_product_id"]), int(row["flipkart_product_id"]))
            if pair in existing_pairs:
                continue  # already stored

            cur.execute(
                """
                INSERT INTO product_matches
                    (amazon_product_id, flipkart_product_id, confidence_score)
                VALUES (?, ?, ?)
                """,
                (pair[0], pair[1], float(row["confidence_score"])),
            )
            existing_pairs.add(pair)
            matches_saved += 1

        conn.commit()

    finally:
        conn.close()

    summary = {
        "total_amazon": len(amazon_df),
        "total_flipkart": len(flipkart_df),
        "matches_found": len(results_df),
        "matches_saved": matches_saved,
    }

    return summary, results_df
