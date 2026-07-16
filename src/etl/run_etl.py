import sqlite3
import pandas as pd

from load_raw import load_raw_files
from validate import validate_rows
from clean import clean_missing
from dedup import deduplicate_within_source
from normalize_names import normalize_product_name
from load_to_db import load_to_db

def create_etl_log_table(conn):
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS etl_run_log (
        run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        records_processed INTEGER,
        status TEXT,
        duplicates_removed INTEGER,
        missing_values_fixed INTEGER,
        invalid_rows_removed INTEGER,
        run_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()

def run_etl():

    # Step 4: Load raw data
    df = load_raw_files("data/raw")

    # Step 5: Validate
    valid_df, invalid_df = validate_rows(df)

    # Step 6: Clean missing values
    cleaned_df, missing_log = clean_missing(valid_df)

    # Step 7: Remove duplicates
    dedup_df, dup_count = deduplicate_within_source(cleaned_df)

    # Step 8: Normalize names
    normalized_df = normalize_product_name(dedup_df)

    # Step 9: Load into DB
    rows_inserted = load_to_db(
        normalized_df,
        "data/price_comparison.db"
    )

    # Step 10: Save invalid rows
    invalid_df.to_csv("invalid_rows.csv", index=False)

    # Step 11: Missing values fixed
    missing_fixed = sum(missing_log.values())

    # Step 12: Log into DB
    conn = sqlite3.connect("data/price_comparison.db")
    create_etl_log_table(conn)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO etl_run_log
    (
        source,
        records_processed,
        status,
        duplicates_removed,
        missing_values_fixed,
        invalid_rows_removed
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """,
    (
        "combined",
        len(df),
        "Success",
        dup_count,
        missing_fixed,
        len(invalid_df)
    ))

    conn.commit()
    conn.close()

    # Step 13: Print summary (IMPORTANT: inside function)
    print("\nETL Pipeline Summary")
    print("-" * 30)
    print(f"Records Processed      : {len(df)}")
    print(f"Rows Inserted          : {rows_inserted}")
    print(f"Duplicates Removed     : {dup_count}")
    print(f"Missing Values Fixed   : {missing_fixed}")
    print(f"Invalid Rows Removed   : {len(invalid_df)}")
    print(f"Status                 : Success")


# Step 14: Run
if __name__ == "__main__":
    run_etl()