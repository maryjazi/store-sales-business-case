"""
Phase 1 - Data Cleaning & Feature Engineering

Starts from the Phase 0 merged dataset and:
  1. Handles missing values (transactions)
  2. Engineers time-based features (calendar + Ecuador payday rule)
  3. Engineers store-lifecycle features (days since a store started operating)
  4. Flags statistical outliers in `sales` (kept, not removed — real demand spikes)
  5. Converts categoricals to `category` dtype for memory efficiency
  6. Builds a matching feature set for test.csv (same transforms, no leakage)

Educational goal: defensible, documented cleaning decisions — every choice below is
backed by a number from the data, not a guess.
"""
import os
import shutil
import pandas as pd
from features import add_time_features, add_store_lifecycle_features

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "data", "raw")
PROCESSED = os.path.join(ROOT, "data", "processed")

# ---- Load Phase 0 output ----
df = pd.read_parquet(f"{PROCESSED}/merged_train.parquet")
print("Loaded merged_train:", df.shape)

# ---- 1. Missing transactions ----
# Phase 0 finding: 245,784 rows have no transaction record, and 98.7% of those also have
# sales == 0 -> these are almost certainly days the store had no (or unlogged) activity.
# Decision: keep an explicit flag before filling, so "no data" stays distinguishable from
# "zero transactions" downstream if needed.
df["transactions_missing"] = df["transactions"].isna()
df["transactions"] = df["transactions"].fillna(0)

# ---- 2. Time features (calendar + Ecuador payday rule) ----
df = add_time_features(df)

# ---- 3. Store lifecycle ----
df = add_store_lifecycle_features(df)
# Save the per-store first-active-date map so test.csv can reuse the exact same reference
# point (must not be recomputed from test, which has no sales column).
store_open_map = df[["store_nbr", "store_first_active_date"]].drop_duplicates()

# ---- 4. Outlier flag on sales (per product family, since scale differs hugely) ----
q999 = df.groupby("family")["sales"].transform(lambda s: s.quantile(0.999))
df["sales_outlier_flag"] = df["sales"] > q999
print(f"Outlier-flagged rows: {df['sales_outlier_flag'].sum()} ({df['sales_outlier_flag'].mean()*100:.2f}%)")

# ---- 5. Categorical dtypes ----
for col in ["family", "city", "state", "type", "cluster", "holiday_type"]:
    df[col] = df[col].astype("category")

print("\nFinal dtypes:")
print(df.dtypes)
print("\nMissing values remaining:\n", df.isna().sum()[df.isna().sum() > 0])

# ---- Save (local first, then copy to the network-mounted folder — mount writes are slow) ----
local_tmp = "/tmp/cleaned_train.parquet"
df.to_parquet(local_tmp, index=False)
shutil.copyfile(local_tmp, f"{PROCESSED}/cleaned_train.parquet")
print(f"\nSaved cleaned_train.parquet ({os.path.getsize(local_tmp)/1e6:.1f} MB)")

# ============================================================
# Build a matching feature set for test.csv (no leakage columns)
# ============================================================
test = pd.read_csv(f"{RAW}/test.csv")
test["date"] = pd.to_datetime(test["date"], format="%Y-%m-%d")

stores = pd.read_csv(f"{RAW}/stores.csv")
oil = pd.read_csv(f"{RAW}/oil.csv")
oil["date"] = pd.to_datetime(oil["date"], format="%Y-%m-%d")
holidays = pd.read_csv(f"{RAW}/holidays_events.csv")
holidays["date"] = pd.to_datetime(holidays["date"], format="%Y-%m-%d")

test = test.merge(stores, on="store_nbr", how="left")

oil_full = oil.set_index("date").reindex(
    pd.date_range(df["date"].min(), test["date"].max(), freq="D")
).rename_axis("date").reset_index()
oil_full["dcoilwtico"] = oil_full["dcoilwtico"].ffill().bfill()
test = test.merge(oil_full, on="date", how="left")

national_holidays = (
    holidays[(holidays["locale"] == "National") & (holidays["transferred"] == False)]
    [["date", "type", "description"]]
    .drop_duplicates(subset="date", keep="first")
    .rename(columns={"type": "holiday_type", "description": "holiday_description"})
)
test = test.merge(national_holidays, on="date", how="left")
test["is_holiday"] = test["holiday_type"].notna()

# NOTE: `transactions` is intentionally NOT added to test. In a real forecasting setting,
# same-day transaction counts are not known in advance -- using them here would leak
# information not actually available at prediction time.

test = add_time_features(test)
test = test.merge(store_open_map, on="store_nbr", how="left")
test["days_since_store_open"] = (test["date"] - test["store_first_active_date"]).dt.days
test["days_since_store_open"] = test["days_since_store_open"].clip(lower=0)

for col in ["family", "city", "state", "type", "cluster", "holiday_type"]:
    test[col] = test[col].astype("category")

local_tmp_test = "/tmp/prepared_test.parquet"
test.to_parquet(local_tmp_test, index=False)
shutil.copyfile(local_tmp_test, f"{PROCESSED}/prepared_test.parquet")
print(f"\nSaved prepared_test.parquet ({test.shape[0]} rows, {os.path.getsize(local_tmp_test)/1e6:.1f} MB)")
