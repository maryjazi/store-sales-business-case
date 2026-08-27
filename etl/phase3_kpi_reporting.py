"""
Phase 3 - KPI Definition & Reporting

Turns the cleaned dataset into a set of business KPIs a retail manager would actually
ask for, at three levels: headline (single numbers), store level, and category level.

Educational goal: KPI design — picking metrics that are (a) directly tied to a business
decision, (b) computed consistently, and (c) documented so anyone can audit them.

All outputs written to /tmp first, then copied to the mounted folder (mount write speed).
"""
import os
import json
import shutil
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
REPORTS = os.path.join(ROOT, "reports")

df = pd.read_parquet(f"{PROCESSED}/cleaned_train.parquet")
with open(f"{REPORTS}/eda_insights.json") as f:
    eda = json.load(f)

print("Loaded cleaned_train:", df.shape)

# ============================================================
# 1. Headline KPIs (single numbers, for an exec summary)
# ============================================================
total_sales = df["sales"].sum()
n_days = df["date"].nunique()
avg_daily_sales = df.groupby("date")["sales"].sum().mean()

yearly = df.groupby("year")["sales"].sum()
# 2017 is a partial year in this dataset (ends Aug 15) -> exclude from clean YoY comparisons
yoy = {}
for y in [2014, 2015, 2016]:
    if y in yearly.index and (y - 1) in yearly.index:
        yoy[f"YoY {y-1}->{y}"] = round((yearly[y] / yearly[y - 1] - 1) * 100, 1)

pct_zero_sales = (df["sales"] == 0).mean() * 100
pct_transactions_missing = df["transactions_missing"].mean() * 100

# sales per transaction (ticket-size proxy), only on store-days with recorded transactions
has_tx = df[df["transactions"] > 0]
sales_per_transaction = (has_tx.groupby(["date", "store_nbr"])["sales"].sum() /
                          has_tx.groupby(["date", "store_nbr"])["transactions"].first()).mean()

headline = {
    "Total Sales (2013-08/2017)": round(float(total_sales), 0),
    "Avg Daily Sales (all stores)": round(float(avg_daily_sales), 0),
    **yoy,
    "Weekend vs Weekday Sales Uplift %": round(eda["weekend_vs_weekday_pct"], 1),
    "National Holiday Sales Uplift %": round(eda["holiday_uplift_pct"], 1),
    "Payday Sales Uplift %": round(eda["payday_uplift_pct"], 1),
    "Oil Price vs Monthly Sales Correlation": round(eda["oil_sales_correlation"], 2),
    "Avg Sales per Transaction (ticket proxy, USD)": round(float(sales_per_transaction), 2),
    "% Rows with Zero Sales": round(float(pct_zero_sales), 1),
    "% Rows with Missing Transaction Data": round(float(pct_transactions_missing), 1),
}

kpi_summary = pd.DataFrame(
    [{"KPI": k, "Value": v} for k, v in headline.items()]
)
print("\n=== HEADLINE KPIs ===")
print(kpi_summary.to_string(index=False))

# ============================================================
# 2. Store-level KPIs
# ============================================================
store_kpi = df.groupby("store_nbr", observed=True).agg(
    total_sales=("sales", "sum"),
    avg_daily_sales=("sales", lambda s: s.sum() / n_days),
    city=("city", "first"),
    state=("state", "first"),
    type=("type", "first"),
    cluster=("cluster", "first"),
).reset_index()
store_kpi["sales_rank"] = store_kpi["total_sales"].rank(ascending=False).astype(int)
store_kpi = store_kpi.sort_values("sales_rank")

print(f"\nTop 5 stores by total sales:\n{store_kpi.head(5)[['store_nbr','city','type','total_sales']]}")
print(f"\nBottom 5 stores by total sales:\n{store_kpi.tail(5)[['store_nbr','city','type','total_sales']]}")

# ============================================================
# 3. Category (product family) KPIs
# ============================================================
cat_kpi = df.groupby("family", observed=True).agg(
    total_sales=("sales", "sum"),
    avg_sales_per_row=("sales", "mean"),
).reset_index()
cat_kpi["share_pct"] = (cat_kpi["total_sales"] / cat_kpi["total_sales"].sum() * 100).round(2)

promo_by_cat = df.groupby(["family", df["onpromotion"] > 0], observed=True)["sales"].mean().unstack()
promo_by_cat.columns = ["avg_sales_no_promo", "avg_sales_with_promo"]
promo_by_cat["promo_uplift_pct"] = (
    (promo_by_cat["avg_sales_with_promo"] / promo_by_cat["avg_sales_no_promo"] - 1) * 100
).round(1)
cat_kpi = cat_kpi.merge(promo_by_cat.reset_index(), on="family", how="left")
cat_kpi = cat_kpi.sort_values("total_sales", ascending=False)

print(f"\nTop 5 categories by promo uplift:\n{cat_kpi.sort_values('promo_uplift_pct', ascending=False).head(5)[['family','promo_uplift_pct']]}")

# ============================================================
# 4. Monthly KPIs (for trend/Power BI)
# ============================================================
monthly_kpi = df.groupby(pd.Grouper(key="date", freq="MS")).agg(
    total_sales=("sales", "sum"),
    avg_oil_price=("dcoilwtico", "mean"),
    n_holidays=("is_holiday", "sum"),
).reset_index()
monthly_kpi["yoy_growth_pct"] = monthly_kpi["total_sales"].pct_change(12).mul(100).round(1)

# ============================================================
# Save everything (local /tmp first, then copy to mount)
# ============================================================
local_dir = "/tmp/kpi_outputs"
os.makedirs(local_dir, exist_ok=True)
kpi_summary.to_csv(f"{local_dir}/kpi_summary.csv", index=False)
store_kpi.to_csv(f"{local_dir}/kpi_store.csv", index=False)
cat_kpi.to_csv(f"{local_dir}/kpi_category.csv", index=False)
monthly_kpi.to_csv(f"{local_dir}/kpi_monthly.csv", index=False)

dest_reports = REPORTS
dest_processed = PROCESSED
shutil.copyfile(f"{local_dir}/kpi_summary.csv", f"{dest_reports}/kpi_summary.csv")
shutil.copyfile(f"{local_dir}/kpi_store.csv", f"{dest_processed}/kpi_store.csv")
shutil.copyfile(f"{local_dir}/kpi_category.csv", f"{dest_processed}/kpi_category.csv")
shutil.copyfile(f"{local_dir}/kpi_monthly.csv", f"{dest_processed}/kpi_monthly.csv")

print("\nSaved: reports/kpi_summary.csv, data/processed/kpi_store.csv, kpi_category.csv, kpi_monthly.csv")
