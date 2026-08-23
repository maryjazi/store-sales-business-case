"""
Phase 0 - Data Understanding
Loads all raw CSVs, inspects structure (shape, dtypes, missing values, date ranges),
merges them into one working dataset, and saves it to data/processed/.

Educational goal: real-world pandas merge/join (SQL JOIN equivalent) and
data-profiling habits before any modeling.
"""
import pandas as pd
import os

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PROCESSED = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
os.makedirs(PROCESSED, exist_ok=True)

def profile(name, df):
    print(f"\n{'='*60}\n{name}\n{'='*60}")
    print("shape:", df.shape)
    print(df.dtypes)
    print("missing values:\n", df.isna().sum()[df.isna().sum() > 0])
    if "date" in df.columns:
        print("date range:", df["date"].min(), "->", df["date"].max())

# ---- Load ----
# Note: parse_dates=[...] inside read_csv is slow on large files (per-row inference).
# Faster: read as string, then pd.to_datetime with an explicit format.
def fast_date(df, col="date"):
    df[col] = pd.to_datetime(df[col], format="%Y-%m-%d")
    return df

train = fast_date(pd.read_csv(f"{RAW}/train.csv"))
test = fast_date(pd.read_csv(f"{RAW}/test.csv"))
stores = pd.read_csv(f"{RAW}/stores.csv")
oil = fast_date(pd.read_csv(f"{RAW}/oil.csv"))
holidays = fast_date(pd.read_csv(f"{RAW}/holidays_events.csv"))
transactions = fast_date(pd.read_csv(f"{RAW}/transactions.csv"))

profile("train", train)
profile("test", test)
profile("stores", stores)
profile("oil", oil)
profile("holidays_events", holidays)
profile("transactions", transactions)

print(f"\nUnique stores: {train['store_nbr'].nunique()}")
print(f"Unique product families: {train['family'].nunique()}")
print(f"Families: {sorted(train['family'].unique())}")

# ---- Merge into one working dataset ----
# 1) attach store metadata (city, state, type, cluster)
df = train.merge(stores, on="store_nbr", how="left")

# 2) attach oil price (fill gaps via forward-fill since oil.csv has weekday-only entries)
oil_full = oil.set_index("date").reindex(
    pd.date_range(oil["date"].min(), oil["date"].max(), freq="D")
).rename_axis("date").reset_index()
oil_full["dcoilwtico"] = oil_full["dcoilwtico"].ffill().bfill()
df = df.merge(oil_full, on="date", how="left")

# 3) attach transactions (store-day level)
df = df.merge(transactions, on=["date", "store_nbr"], how="left")

# 4) attach holiday flag (national holidays only, to avoid store/locale mismatch complexity in phase 0)
# NOTE: some dates have more than one national holiday record (e.g. a holiday plus its
# "transferred" counterpart). Without de-duplication this fans out the merge and inflates
# row count (caught during Phase 0: 3,000,888 -> 3,008,016 rows). Keep first record per date.
national_holidays = (
    holidays[(holidays["locale"] == "National") & (holidays["transferred"] == False)]
    [["date", "type", "description"]]
    .drop_duplicates(subset="date", keep="first")
    .rename(columns={"type": "holiday_type", "description": "holiday_description"})
)
df = df.merge(national_holidays, on="date", how="left")
df["is_holiday"] = df["holiday_type"].notna()

print(f"\nMerged dataset shape: {df.shape}")
print(df.head())
print("\nMissing values after merge:\n", df.isna().sum()[df.isna().sum() > 0])

# ---- Save ----
# Write to local /tmp first, then copy to the (slower, network-mounted) processed folder.
# Writing parquet directly onto the mount was ~5x slower / risked truncation on timeout.
import shutil
local_tmp = "/tmp/merged_train.parquet"
df.to_parquet(local_tmp, index=False)
shutil.copyfile(local_tmp, f"{PROCESSED}/merged_train.parquet")
print(f"\nSaved merged dataset to {PROCESSED}/merged_train.parquet")
print(f"File size: {os.path.getsize(f'{PROCESSED}/merged_train.parquet') / 1e6:.1f} MB")
