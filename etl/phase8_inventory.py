"""
Phase 8 - Inventory & Merchandising (B4)

Derives stock on hand from the phase-7 receipt flow. Nothing here is a free-standing
inventory invention: every unit in stock arrived through a purchase order that phase 7
raised against the real demand signal.

THE LINEAGE, reconstructable for every store x family x date:

    PO -> Receipt -> Opening Inventory -> Observed Units
                  -> Fulfilled Units_sim -> Unfulfilled Units_sim -> Closing Inventory

THE INVENTORY EQUATION (auditable, no balancing plug, no hidden stock adjustment):

    available_t     = opening_t + receipts_t
    fulfilled_t     = min(observed_units_t, available_t)
    unfulfilled_t   = max(observed_units_t - available_t, 0)
    closing_t       = available_t - fulfilled_t
    opening_t+1     = closing_t

Closing stock can therefore never go negative, but a shortage is never hidden either - it
surfaces as `unfulfilled_units_sim` instead of being absorbed by an adjustment.

WHAT `unfulfilled_units_sim` IS NOT
-----------------------------------
Observed Favorita sales are NOT true demand. If the data says 10 units sold on a day, we
cannot know whether demand was 10, or 15 with 5 lost to a stockout - the dataset has no
inventory and no demand column. So when this simulation's stock cannot cover the observed
quantity, the gap is a shortage **of this simulated supply chain against the observed sales
quantity**. It is NOT Favorita's historical lost sales, and no output may call it that.
For the same reason every rate below is a *simulated* OOS rate, never an actual one.

Initialisation (documented assumption): opening stock on the first date of each
store x family series is 14 days of cover, based on that series' average daily units over
its first 90 days. Series with no early activity start at zero.

Outputs (data/processed/):
  fact_inventory_sim.parquet - grain: date x store x family (3,000,888 rows)
  kpi_inventory_sim.csv      - merchandising KPIs per family

NAMING: the store-side rate here is `simulated_demand_fulfillment_rate_pct`
(fulfilled_sim / observed_units). It is NOT a supplier service level - supplier OTD and
in-full stay in the procurement layer (phase 7). The two must never be read as one number.
  kpi_inventory_store_sim.csv - merchandising KPIs per store
"""
import os
import shutil

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
LOCAL = "/tmp/inventory_layer"
os.makedirs(LOCAL, exist_ok=True)

INIT_COVER_DAYS = 14
INIT_WINDOW_DAYS = 90
GROUP = ["store_nbr", "family"]


def opening_stock_seed(df):
    """14 days of cover from the first 90 days of each series (documented assumption)."""
    first = df.groupby(GROUP, observed=True)["date"].transform("min")
    early = df["date"] < first + pd.Timedelta(days=INIT_WINDOW_DAYS)
    seed = (df.loc[early].groupby(GROUP, observed=True)["units"].mean() * INIT_COVER_DAYS)
    return seed.round(0).clip(lower=0)


def main():
    sales_path = os.path.join(PROCESSED, "fact_sales_commercial.parquet")
    po_path = os.path.join(PROCESSED, "fact_purchase_order_sim.parquet")
    for p in (sales_path, po_path):
        if not os.path.exists(p):
            raise SystemExit("missing %s - run phases 6 and 7 first" % os.path.basename(p))

    df = pd.read_parquet(sales_path, columns=["date", "store_nbr", "family", "units",
                                              "unit_cost_sim", "net_price_sim"])
    df["family"] = df["family"].astype(str)
    df = df.sort_values(GROUP + ["date"]).reset_index(drop=True)
    print("sales grid:", df.shape)

    po = pd.read_parquet(po_path, columns=["receipt_date", "store_nbr", "family", "received_qty"])
    po["family"] = po["family"].astype(str)
    receipts = (po.groupby(["store_nbr", "family", "receipt_date"], observed=True)["received_qty"]
                  .sum().reset_index()
                  .rename(columns={"receipt_date": "date", "received_qty": "receipts"}))
    df = df.merge(receipts, on=["store_nbr", "family", "date"], how="left")
    df["receipts"] = df["receipts"].fillna(0.0)
    # receipts landing after the last sales date cannot be booked into the grid
    late = receipts["date"] > df["date"].max()
    print("receipts merged: %.0f units (%d receipt lines fall past the sales window)"
          % (df["receipts"].sum(), int(late.sum())))

    # ---- the recursion, run exactly (no closed-form shortcut, no float drift) ----
    # The sales grid is complete and rectangular (every store x family has every date), so the
    # series can be reshaped to a (group x day) matrix and the recursion stepped one day at a
    # time across all groups at once: 1,684 exact iterations instead of a cumulative formula.
    seed = opening_stock_seed(df)
    keys = df[GROUP].drop_duplicates().reset_index(drop=True)
    n_groups, n_days = len(keys), df["date"].nunique()
    if n_groups * n_days != len(df):
        raise SystemExit("sales grid is not rectangular - the matrix recursion needs a full grid")

    units_m = df["units"].to_numpy(dtype="float64").reshape(n_groups, n_days)
    recv_m = df["receipts"].to_numpy(dtype="float64").reshape(n_groups, n_days)
    opening_m = np.empty_like(units_m)
    fulfilled_m = np.empty_like(units_m)
    closing_m = np.empty_like(units_m)

    carry = keys.set_index(GROUP).index.map(seed).to_numpy(dtype="float64")
    carry = np.nan_to_num(carry, nan=0.0)
    for t_i in range(n_days):
        opening_m[:, t_i] = carry
        available = carry + recv_m[:, t_i]
        fulfilled = np.minimum(units_m[:, t_i], available)
        carry = available - fulfilled              # closing, never negative by construction
        fulfilled_m[:, t_i] = fulfilled
        closing_m[:, t_i] = carry

    df["opening_stock"] = opening_m.reshape(-1)
    df["closing_stock"] = closing_m.reshape(-1)
    df["fulfilled_units_sim"] = fulfilled_m.reshape(-1)
    df["available"] = df["opening_stock"] + df["receipts"]
    df["unfulfilled_units_sim"] = (df["units"] - df["fulfilled_units_sim"]).clip(lower=0)

    # ---- audit: the equation must close exactly, with no plug ----
    residual = (df["available"] - df["fulfilled_units_sim"] - df["closing_stock"]).abs()
    if residual.max() > 1e-9:
        raise SystemExit("inventory equation does not reconcile: max residual %.3e" % residual.max())
    carry_break = (df.groupby(GROUP, observed=True)["closing_stock"].shift(1)
                   - df["opening_stock"]).abs()
    if carry_break.max(skipna=True) > 1e-9:
        raise SystemExit("opening stock does not carry the previous closing stock")
    if (df["closing_stock"] < 0).any():
        raise SystemExit("negative closing stock")
    print("lineage reconciles exactly: closing = opening + receipts - fulfilled, "
          "opening_t+1 = closing_t, no negative stock")

    df["inventory_value_at_cost_sim"] = df["closing_stock"] * df["unit_cost_sim"]
    df["fulfilled_revenue_sim"] = df["fulfilled_units_sim"] * df["net_price_sim"]
    df["fulfilled_cogs_sim"] = df["fulfilled_units_sim"] * df["unit_cost_sim"]
    df["fulfilled_margin_sim"] = df["fulfilled_revenue_sim"] - df["fulfilled_cogs_sim"]
    df["stockout_day_sim"] = df["unfulfilled_units_sim"] > 0
    df["zero_stock_day_sim"] = df["closing_stock"] <= 0

    fact = df[["date", "store_nbr", "family", "units", "receipts", "opening_stock", "available",
               "fulfilled_units_sim", "unfulfilled_units_sim", "closing_stock",
               "inventory_value_at_cost_sim", "fulfilled_revenue_sim", "fulfilled_cogs_sim",
               "fulfilled_margin_sim", "stockout_day_sim", "zero_stock_day_sim"]].copy()
    fact = fact.rename(columns={"units": "observed_units"})
    # The lineage columns stay float64 on disk: the audit (closing = opening + receipts -
    # fulfilled) has to hold in the delivered artifact, not only in memory, and float32 loses
    # enough precision at million-unit magnitudes to break it. Derived value columns, which
    # nothing reconciles against, are stored as float32.
    lineage = ["observed_units", "receipts", "opening_stock", "available",
               "fulfilled_units_sim", "unfulfilled_units_sim", "closing_stock"]
    for col in fact.columns:
        if fact[col].dtype == "float64" and col not in lineage:
            fact[col] = fact[col].astype("float32")
    fact["store_nbr"] = fact["store_nbr"].astype("int16")
    fact["family"] = fact["family"].astype("category")

    span_days = (fact["date"].max() - fact["date"].min()).days
    years, weeks = span_days / 365.25, span_days / 7.0

    def kpis(keys):
        """Merchandising KPIs. Average inventory is the DAILY TOTAL stock averaged over days -
        not the mean of row-level values, which would divide by the number of rows and inflate
        turnover. Turnover and GMROI are annualised over the %.1f-year window.""" % years
        totals = fact.groupby(keys, observed=True).agg(
            observed_units=("observed_units", "sum"),
            fulfilled_units=("fulfilled_units_sim", "sum"),
            unfulfilled_units=("unfulfilled_units_sim", "sum"),
            receipts=("receipts", "sum"),
            fulfilled_cogs=("fulfilled_cogs_sim", "sum"),
            fulfilled_margin=("fulfilled_margin_sim", "sum"),
            oos_day_share=("stockout_day_sim", "mean"),
            zero_stock_day_share=("zero_stock_day_sim", "mean"),
        )
        daily = (fact.groupby(keys + ["date"], observed=True)
                     [["closing_stock", "inventory_value_at_cost_sim"]].sum())
        avg = daily.groupby(keys, observed=True).mean().rename(columns={
            "closing_stock": "avg_inventory_units",
            "inventory_value_at_cost_sim": "avg_inventory_value"})
        opening_start = (fact[fact["date"] == fact["date"].min()]
                         .groupby(keys, observed=True)["opening_stock"].sum()
                         .rename("opening_stock_start"))
        out = totals.join(avg).join(opening_start)

        goods_handled = out["opening_stock_start"] + out["receipts"]
        out["sell_through_pct_sim"] = 100 * out["fulfilled_units"] / goods_handled.replace(0, np.nan)
        out["simulated_demand_fulfillment_rate_pct"] = 100 * out["fulfilled_units"] / out["observed_units"].replace(0, np.nan)
        out["stock_turnover_pa_sim"] = (out["fulfilled_cogs"] / years) / out["avg_inventory_value"].replace(0, np.nan)
        out["weeks_of_supply_sim"] = out["avg_inventory_units"] / (
            out["fulfilled_units"].replace(0, np.nan) / weeks)
        out["gmroi_pa_sim"] = (out["fulfilled_margin"] / years) / out["avg_inventory_value"].replace(0, np.nan)
        out["simulated_oos_day_rate_pct"] = 100 * out["oos_day_share"]
        out["zero_stock_day_rate_pct_sim"] = 100 * out["zero_stock_day_share"]
        return out.drop(columns=["oos_day_share", "zero_stock_day_share"]).round(3).reset_index()

    kpi_family = kpis(["family"])
    kpi_store = kpis(["store_nbr"])

    fact.to_parquet(f"{LOCAL}/fact_inventory_sim.parquet", index=False)
    kpi_family.to_csv(f"{LOCAL}/kpi_inventory_sim.csv", index=False)
    kpi_store.to_csv(f"{LOCAL}/kpi_inventory_store_sim.csv", index=False)
    for name in ("fact_inventory_sim.parquet", "kpi_inventory_sim.csv",
                 "kpi_inventory_store_sim.csv"):
        shutil.copyfile(f"{LOCAL}/{name}", os.path.join(PROCESSED, name))

    tot_obs = fact["observed_units"].sum()
    tot_ful = fact["fulfilled_units_sim"].sum()
    print("\n--- inventory scenario summary (simulated; docs/21) ---")
    print("observed units (real)        : %.0f" % tot_obs)
    print("fulfilled units (sim)        : %.0f (%.1f%% demand fulfillment rate)"
          % (tot_ful, 100 * tot_ful / tot_obs))
    print("unfulfilled units (sim)      : %.0f  <- shortage vs observed quantity, NOT lost sales"
          % fact["unfulfilled_units_sim"].sum())
    print("simulated OOS day rate       : %.1f%%" % (100 * fact["stockout_day_sim"].mean()))
    print("zero-stock day rate (sim)    : %.1f%%" % (100 * fact["zero_stock_day_sim"].mean()))
    print("avg inventory value (sim)    : %.0f USD"
          % fact["inventory_value_at_cost_sim"].mean())
    print("\nfamily KPIs - 3 lowest sell-through:\n%s"
          % kpi_family.nsmallest(3, "sell_through_pct_sim")[
              ["family", "sell_through_pct_sim", "weeks_of_supply_sim", "gmroi_pa_sim"]].to_string(index=False))
    print("\nfamily KPIs - 3 highest simulated OOS rate:\n%s"
          % kpi_family.nlargest(3, "simulated_oos_day_rate_pct")[
              ["family", "simulated_oos_day_rate_pct", "simulated_demand_fulfillment_rate_pct",
               "stock_turnover_pa_sim"]].to_string(index=False))
    print("\nwritten to %s" % PROCESSED)


if __name__ == "__main__":
    main()
