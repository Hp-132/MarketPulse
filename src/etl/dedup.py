import pandas as pd
def deduplicate_within_source(df):
    df = df.copy()
    df["scraped_at"] = pd.to_datetime(df["scraped_at"])
    df = df.sort_values(
    by="scraped_at",
    ascending=False
)
    original_rows = len(df)
    df = df.drop_duplicates(
    subset=["source", "external_id"],
    keep="first"
)
    duplicates_removed = original_rows - len(df)
    return df, duplicates_removed

if __name__ == "__main__":

    from load_raw import load_raw_files
    from validate import validate_rows
    from clean import clean_missing

    df = load_raw_files("data/raw")

    valid_df, invalid_df = validate_rows(df)

    cleaned_df, changes = clean_missing(valid_df)

    dedup_df, removed = deduplicate_within_source(cleaned_df)

    print("Duplicates Removed:", removed)

    print("Rows Before:", len(cleaned_df))

    print("Rows After:", len(dedup_df))
    