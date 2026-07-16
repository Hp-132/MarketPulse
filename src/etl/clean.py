import pandas as pd
def clean_missing(df):
    df = df.copy()
    changes = {
    "review_count": 0,
    "availability": 0,
    "discount_pct": 0
}
    changes["review_count"] = df["review_count"].isna().sum()
    df["review_count"] = df["review_count"].fillna(0)

    changes["availability"] = df["availability"].isna().sum()
    df["availability"] = df["availability"].fillna("unknown")

    mask = (
    df["discount_pct"].isna()
    & df["current_price"].notna()
    & df["mrp"].notna()
)
    changes["discount_pct"] = int(mask.sum())
    df.loc[mask, "discount_pct"] = (
        (1 - df.loc[mask, "current_price"] / df.loc[mask, "mrp"])
        * 100
    ).round(1)
    
    return df, changes

if __name__ == "__main__":
    from load_raw import load_raw_files
    from validate import validate_rows

    df = load_raw_files("data/raw")

    valid_df, invalid_df = validate_rows(df)

    cleaned_df, changes = clean_missing(valid_df)

    print(changes)

    print(cleaned_df.head())


    
