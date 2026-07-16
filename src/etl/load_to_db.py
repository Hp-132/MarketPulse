import sqlite3
import os
import math

def _safe_float(val):
    """Return float or None — never NaN/Inf."""
    try:
        v = float(val)
        return None if (math.isnan(v) or math.isinf(v)) else v
    except (TypeError, ValueError):
        return None

def load_to_db(df, db_path):
    print("Database Path:", os.path.abspath(db_path))
    print("Database Exists:", os.path.exists(db_path))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    rows_inserted = 0
    for _, row in df.iterrows():
        try:
            cursor.execute("""
INSERT INTO products
(
    source,
    product_name,
    brand,
    category,
    current_price,
    mrp,
    discount_pct,
    currency,
    product_url
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""",
(
    row["source"],
    row["product_name_clean"],
    row["brand"],
    row["category"],
    _safe_float(row.get("current_price")),
    _safe_float(row.get("mrp")),
    _safe_float(row.get("discount_pct")),
    row["currency"],
    row["product_url"]
))
            product_id = cursor.lastrowid

            cursor.execute("""
INSERT INTO price_history
(
    product_id,
    price,
    recorded_at
)
VALUES (?, ?, ?)
""",
(
    product_id,
    row["current_price"],
    str(row["scraped_at"]) 
))
            cursor.execute("""
INSERT INTO reviews
(
    product_id,
    rating,
    review_count,
    sentiment_score
)
VALUES (?, ?, ?, ?)
""",
(
    product_id,
    row["rating"],
    row["review_count"],
    None
))
            conn.commit()
            rows_inserted += 1
        except Exception as e:
            conn.rollback()
            print("Error:", e)
    conn.close()
    return rows_inserted

if __name__ == "__main__":

    from load_raw import load_raw_files
    from validate import validate_rows
    from clean import clean_missing
    from dedup import deduplicate_within_source
    from normalize_names import normalize_product_name

    df = load_raw_files("data/raw")

    valid_df, invalid_df = validate_rows(df)

    cleaned_df, changes = clean_missing(valid_df)

    dedup_df, removed = deduplicate_within_source(cleaned_df)

    normalized_df = normalize_product_name(dedup_df)

    inserted = load_to_db(
        normalized_df,
        "database/marketpulse.db"
    )

    print("Rows Inserted:", inserted)
