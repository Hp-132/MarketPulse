import pandas as pd
from pathlib import Path

def load_raw_files(raw_dir):
    all_data=[]
    raw_path = Path(raw_dir)
    json_files = raw_path.glob("*.json")
    for file in json_files:
        df = pd.read_json(file)
        if df.empty:
            continue
        if "asin" in df.columns:
            df["external_id"] = df["asin"]
        elif "pid" in df.columns:
            df["external_id"] = df["pid"]
        all_data.append(df)
    combined_df = pd.concat(all_data, ignore_index=True)
    return combined_df

if __name__ == "__main__":
    df = load_raw_files("data/raw")

    print(df.head())
    print(df.shape)
    print(df.columns)