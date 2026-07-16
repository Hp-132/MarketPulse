import pandas as pd
import re

def normalize_product_name(df):
    df = df.copy()

    def clean_name(name):
        if pd.isna(name):
            return name

        # Replace | with a space
        name = name.replace("|", " ")

        # Remove trademark symbols
        for symbol in ["®", "™", "©"]:
            name = name.replace(symbol, "")

        # Remove extra spaces
        name = re.sub(r"\s+", " ", name)

        # Remove leading/trailing spaces
        return name.strip()

    # Create a NEW cleaned column
    df["product_name_clean"] = df["product_name"].apply(clean_name)

    return df


if __name__ == "__main__":

    from load_raw import load_raw_files
    from validate import validate_rows
    from clean import clean_missing
    from dedup import deduplicate_within_source

    df = load_raw_files("data/raw")

    valid_df, invalid_df = validate_rows(df)

    cleaned_df, changes = clean_missing(valid_df)

    dedup_df, removed = deduplicate_within_source(cleaned_df)

    normalized_df = normalize_product_name(dedup_df)

    print(normalized_df[["product_name", "product_name_clean"]].head())