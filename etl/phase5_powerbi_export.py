"""
Phase 5 - Power BI Data Export

Builds a proper star schema (fact + dimension tables) for Power BI, instead of handing
over one flat table. This is the modeling pattern Power BI is actually designed for:
smaller dimensions, DAX relationships, fast slicers.

Tables produced (dashboard/data/):
  fact_sales_actual.parquet   - grain: date x store x family, historical (2013-2017)
  fact_sales_forecast.parquet - grain: date x store x family, forecast (Aug 16-31 2017)
  dim_store.csv                - one row per store
  dim_date.csv                 - one row per calendar date (covers actual + forecast range)
  dim_family.csv                - one row per product family, with a business-friendly grouping

Power BI Desktop reads Parquet natively (Get Data > Parquet), so the large fact table
does not need to be flattened to CSV.
"""
import os
import shutil
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
DASH_LOCAL = "/tmp/dashboard_data"
os.makedirs(DASH_LOCAL, exist_ok=True)

df = pd.read_parquet(f"{PROCESSED}/cleaned_train.parquet")
forecast = pd.read_parquet(f"{PROCESSED}/forecast_detail.parquet")
print("loaded:", df.shape, forecast.shape)

# ---- Fact: actual sales ----
fact_actual = df[[
    "date", "store_nbr", "family", "sales", "onpromotion",
    "is_holiday", "is_payday", "is_weekend", "sales_outlier_flag", "transactions",
]].copy()
fact_actual.to_parquet(f"{DASH_LOCAL}/fact_sales_actual.parquet", index=False)

# ---- Fact: forecast sales ----
fact_forecast = forecast[["date", "store_nbr", "family", "sales"]].rename(
    columns={"sales": "forecast_sales"}
)
fact_forecast.to_parquet(f"{DASH_LOCAL}/fact_sales_forecast.parquet", index=False)

# ---- Dim: store ----
dim_store = df[["store_nbr", "city", "state", "type", "cluster"]].drop_duplicates()
dim_store["store_first_active_date"] = df.groupby("store_nbr")["store_first_active_date"].first().values
dim_store.to_csv(f"{DASH_LOCAL}/dim_store.csv", index=False)

# ---- Dim: date (covers both actual + forecast range) ----
full_range = pd.date_range(df["date"].min(), forecast["date"].max(), freq="D")
dim_date = pd.DataFrame({"date": full_range})
dim_date["year"] = dim_date["date"].dt.year
dim_date["month"] = dim_date["date"].dt.month
dim_date["month_name"] = dim_date["date"].dt.month_name()
dim_date["day"] = dim_date["date"].dt.day
dim_date["day_of_week"] = dim_date["date"].dt.dayofweek
dim_date["day_name"] = dim_date["date"].dt.day_name()
dim_date["week_of_year"] = dim_date["date"].dt.isocalendar().week.astype(int)
dim_date["quarter"] = dim_date["date"].dt.quarter
dim_date["is_weekend"] = dim_date["day_of_week"].isin([5, 6])
dim_date["is_month_start"] = dim_date["date"].dt.is_month_start
dim_date["is_month_end"] = dim_date["date"].dt.is_month_end
dim_date["is_payday"] = (dim_date["day"] == 15) | dim_date["is_month_end"]
dim_date.to_csv(f"{DASH_LOCAL}/dim_date.csv", index=False)

# ---- Dim: family (with a business-friendly grouping for drill-down / slicers) ----
FAMILY_GROUPS = {
    "BEVERAGES": "Food & Beverage", "BREAD/BAKERY": "Food & Beverage", "DAIRY": "Food & Beverage",
    "DELI": "Food & Beverage", "EGGS": "Food & Beverage", "FROZEN FOODS": "Food & Beverage",
    "GROCERY I": "Food & Beverage", "GROCERY II": "Food & Beverage", "MEATS": "Food & Beverage",
    "POULTRY": "Food & Beverage", "PREPARED FOODS": "Food & Beverage", "PRODUCE": "Food & Beverage",
    "SEAFOOD": "Food & Beverage", "LIQUOR,WINE,BEER": "Food & Beverage",
    "BEAUTY": "Personal Care & Health", "PERSONAL CARE": "Personal Care & Health",
    "BABY CARE": "Personal Care & Health",
    "CLEANING": "Home & Household", "HOME CARE": "Home & Household",
    "HOME AND KITCHEN I": "Home & Household", "HOME AND KITCHEN II": "Home & Household",
    "HOME APPLIANCES": "Home & Household", "HARDWARE": "Home & Household",
    "LAWN AND GARDEN": "Home & Household",
    "LADIESWEAR": "Apparel", "LINGERIE": "Apparel",
    "PLAYERS AND ELECTRONICS": "Electronics & Leisure", "BOOKS": "Electronics & Leisure",
    "MAGAZINES": "Electronics & Leisure", "SCHOOL AND OFFICE SUPPLIES": "Electronics & Leisure",
    "AUTOMOTIVE": "Automotive & Pets", "PET SUPPLIES": "Automotive & Pets",
    "CELEBRATION": "Other",
}
dim_family = pd.DataFrame({"family": df["family"].cat.categories})
dim_family["family_group"] = dim_family["family"].map(FAMILY_GROUPS).fillna("Other")
dim_family.to_csv(f"{DASH_LOCAL}/dim_family.csv", index=False)

print("Local files ready:", os.listdir(DASH_LOCAL))

# ---- Copy to mounted dashboard/data folder ----
dest = os.path.join(ROOT, "dashboard", "data")
os.makedirs(dest, exist_ok=True)
for fname in os.listdir(DASH_LOCAL):
    shutil.copyfile(f"{DASH_LOCAL}/{fname}", f"{dest}/{fname}")
    print(f"copied {fname} ({os.path.getsize(f'{DASH_LOCAL}/{fname}')/1e6:.2f} MB)")
