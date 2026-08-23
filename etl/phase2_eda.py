"""
Phase 2 - Exploratory Data Analysis (Sales Analytics)

Answers: how do sales move over time, which stores/categories/regions drive them,
and how much do external factors (holidays, payday, oil price) matter?

Educational goal: turning a cleaned dataset into visual, business-readable evidence
(the same charts a Sales Analytics function would produce for stakeholders).

All figures are written locally to /tmp first, then copied to the network-mounted
reports/figures folder (mount writes are slow / risk truncation on large sequential I/O).
"""
import os
import shutil
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

plt.rcParams["figure.dpi"] = 110
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.3

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
LOCAL_FIG_DIR = "/tmp/figures"
os.makedirs(LOCAL_FIG_DIR, exist_ok=True)

df = pd.read_parquet(f"{PROCESSED}/cleaned_train.parquet")
print("Loaded cleaned_train:", df.shape)

def money_fmt(ax, axis="y"):
    fmt = mticker.FuncFormatter(lambda x, _: f"{x/1e6:.1f}M" if abs(x) >= 1e6 else f"{x/1e3:.0f}K")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)

insights = {}

# 1. Daily sales trend with 30-day rolling average
daily = df.groupby("date")["sales"].sum().reset_index()
daily["rolling_30d"] = daily["sales"].rolling(30, min_periods=1).mean()
fig, ax = plt.subplots(figsize=(11, 4.5))
ax.plot(daily["date"], daily["sales"], alpha=0.3, linewidth=0.7, label="Daily total sales")
ax.plot(daily["date"], daily["rolling_30d"], linewidth=2, color="firebrick", label="30-day rolling avg")
ax.set_title("Total Daily Sales Over Time (2013-2017)")
ax.set_ylabel("Sales")
money_fmt(ax)
ax.legend()
fig.tight_layout()
fig.savefig(f"{LOCAL_FIG_DIR}/01_daily_sales_trend.png")
plt.close(fig)

# 2. Sales by year (growth) and by month (seasonality)
df["year"] = df["year"].astype(int)
yearly = df.groupby("year")["sales"].sum()
monthly_avg = df.groupby("month")["sales"].sum().groupby(level=0).mean()  # total by month-of-year across years
monthly_seasonal = df.groupby("month")["sales"].mean()

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
axes[0].bar(yearly.index.astype(str), yearly.values, color="steelblue")
axes[0].set_title("Total Sales by Year")
money_fmt(axes[0])
axes[1].plot(monthly_seasonal.index, monthly_seasonal.values, marker="o", color="darkorange")
axes[1].set_title("Avg Sales per Transaction-Row by Month\n(seasonality)")
axes[1].set_xticks(range(1, 13))
fig.tight_layout()
fig.savefig(f"{LOCAL_FIG_DIR}/02_yearly_monthly.png")
plt.close(fig)
insights["yoy_growth_2013_2016"] = float((yearly.get(2016, 0) / yearly.get(2013, 1) - 1) * 100)

# 3. Day-of-week seasonality
dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
dow = df.groupby("day_of_week")["sales"].mean()
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar([dow_names[i] for i in dow.index], dow.values, color="teal")
ax.set_title("Average Sales by Day of Week")
fig.tight_layout()
fig.savefig(f"{LOCAL_FIG_DIR}/03_day_of_week.png")
plt.close(fig)
insights["weekend_vs_weekday_pct"] = float(
    (df[df["is_weekend"]]["sales"].mean() / df[~df["is_weekend"]]["sales"].mean() - 1) * 100
)

# 4. Top 15 product families by total sales
fam = df.groupby("family", observed=True)["sales"].sum().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(8, 6))
fam.head(15).sort_values().plot.barh(ax=ax, color="mediumseagreen")
ax.set_title("Top 15 Product Families by Total Sales")
money_fmt(ax, axis="x")
fig.tight_layout()
fig.savefig(f"{LOCAL_FIG_DIR}/04_top_families.png")
plt.close(fig)
insights["top3_families"] = fam.head(3).index.tolist()
insights["top3_families_share_pct"] = float(fam.head(3).sum() / fam.sum() * 100)

# 5. Sales by store type
type_sales = df.groupby("type", observed=True)["sales"].sum().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(6, 4))
type_sales.plot.bar(ax=ax, color="slateblue")
ax.set_title("Total Sales by Store Type")
money_fmt(ax)
fig.tight_layout()
fig.savefig(f"{LOCAL_FIG_DIR}/05_store_type.png")
plt.close(fig)

# 6. Top 10 cities by total sales
city_sales = df.groupby("city", observed=True)["sales"].sum().sort_values(ascending=False).head(10)
fig, ax = plt.subplots(figsize=(8, 5))
city_sales.sort_values().plot.barh(ax=ax, color="chocolate")
ax.set_title("Top 10 Cities by Total Sales")
money_fmt(ax, axis="x")
fig.tight_layout()
fig.savefig(f"{LOCAL_FIG_DIR}/06_top_cities.png")
plt.close(fig)

# 7. Holiday effect
holiday_avg = df.groupby("is_holiday")["sales"].mean()
fig, ax = plt.subplots(figsize=(5, 4))
ax.bar(["Regular day", "National holiday"], [holiday_avg.get(False, 0), holiday_avg.get(True, 0)],
       color=["gray", "crimson"])
ax.set_title("Average Sales: Regular Day vs National Holiday")
fig.tight_layout()
fig.savefig(f"{LOCAL_FIG_DIR}/07_holiday_effect.png")
plt.close(fig)
insights["holiday_uplift_pct"] = float((holiday_avg.get(True, 0) / holiday_avg.get(False, 1) - 1) * 100)

# 8. Payday effect
payday_avg = df.groupby("is_payday")["sales"].mean()
fig, ax = plt.subplots(figsize=(5, 4))
ax.bar(["Regular day", "Payday (15th/month-end)"], [payday_avg.get(False, 0), payday_avg.get(True, 0)],
       color=["gray", "seagreen"])
ax.set_title("Average Sales: Regular Day vs Payday")
fig.tight_layout()
fig.savefig(f"{LOCAL_FIG_DIR}/08_payday_effect.png")
plt.close(fig)
insights["payday_uplift_pct"] = float((payday_avg.get(True, 0) / payday_avg.get(False, 1) - 1) * 100)

# 9. Oil price vs sales (monthly correlation)
monthly = df.groupby(pd.Grouper(key="date", freq="MS")).agg(sales=("sales", "sum"), oil=("dcoilwtico", "mean"))
fig, ax1 = plt.subplots(figsize=(11, 4.5))
ax2 = ax1.twinx()
ax1.plot(monthly.index, monthly["sales"], color="steelblue", label="Monthly sales")
ax2.plot(monthly.index, monthly["oil"], color="black", linestyle="--", label="Avg oil price")
ax1.set_ylabel("Monthly sales", color="steelblue")
ax2.set_ylabel("Oil price (WTI, USD)", color="black")
ax1.set_title("Monthly Sales vs Oil Price")
money_fmt(ax1)
fig.tight_layout()
fig.savefig(f"{LOCAL_FIG_DIR}/09_oil_vs_sales.png")
plt.close(fig)
insights["oil_sales_correlation"] = float(monthly["sales"].corr(monthly["oil"]))

# 10. Onpromotion effect
promo = df.groupby(df["onpromotion"] > 0)["sales"].mean()
insights["promo_uplift_pct"] = float((promo.get(True, 0) / promo.get(False, 1) - 1) * 100)

print("\nKEY INSIGHTS:")
for k, v in insights.items():
    print(f"  {k}: {v}")

# ---- Copy all figures to the mounted reports/figures folder ----
dest_dir = os.path.join(ROOT, "reports", "figures")
os.makedirs(dest_dir, exist_ok=True)
for fname in sorted(os.listdir(LOCAL_FIG_DIR)):
    shutil.copyfile(f"{LOCAL_FIG_DIR}/{fname}", f"{dest_dir}/{fname}")
print(f"\nCopied {len(os.listdir(LOCAL_FIG_DIR))} figures to {dest_dir}")

# ---- Save insights as JSON for reuse in later phases (KPI report, business case) ----
import json
with open("/tmp/eda_insights.json", "w") as f:
    json.dump(insights, f, indent=2, default=str)
shutil.copyfile("/tmp/eda_insights.json", os.path.join(ROOT, "reports", "eda_insights.json"))
print("Saved reports/eda_insights.json")
