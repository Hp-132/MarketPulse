import pandas as pd

def validate_rows(df):
    df = df.copy()
    df["reason"] = ""
    invalid_price = (
    df["current_price"].isna()
    | (df["current_price"] <= 0)
)
    invalid_name = (
    df["product_name"].isna()
    | (df["product_name"].str.strip() == "")
)
    invalid_rating = (
    df["rating"].notna()
    & (
        (df["rating"] < 0)
        | (df["rating"] > 5)
    )
)
    invalid_mrp = (
    df["mrp"].notna()
    & (df["mrp"] < df["current_price"])
)
    df.loc[invalid_price, "reason"] += "Invalid price; "
    df.loc[invalid_name, "reason"] += "Missing product name; "
    df.loc[invalid_rating, "reason"] += "Invalid rating; "
    df.loc[invalid_mrp, "reason"] += "MRP lower than current price; "

    invalid_df = df[df["reason"] != ""]
    valid_df = df[df["reason"] == ""]
    
    print("Validation Summary")
    print("------------------")
    print("Invalid Price:", invalid_price.sum())
    print("Missing Product Name:", invalid_name.sum())
    print("Invalid Rating:", invalid_rating.sum())
    print("Invalid MRP:", invalid_mrp.sum())
    print("Total Invalid Rows:", len(invalid_df))
    print("Total Valid Rows:", len(valid_df))

    return valid_df, invalid_df

if __name__ == "__main__":
    from load_raw import load_raw_files

    df = load_raw_files("data/raw")

    valid_df, invalid_df = validate_rows(df)

    print(valid_df.head())
    print(invalid_df.head())

