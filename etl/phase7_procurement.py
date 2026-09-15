"""
Phase 7 - Procurement Foundation (B6)

Builds the supply side of the commercial case: WHO the goods were bought from, WHEN they
were ordered, WHEN they actually arrived, and AT WHAT PRICE. Nothing here is in the
competition data - suppliers, purchase orders and receipts are all simulated.

This phase deliberately stops before inventory. Phase 8 derives stock on hand from the
receipt flow produced here (opening stock + receipts - sales), so that inventory is a
*consequence* of procurement rather than a second, independent invention. If inventory were
generated here, sell-through and out-of-stock would be assumptions instead of results.

Provenance (docs/19 §2):
  * P-07: a table whose NAME ends in `_sim` is simulated in its entirety; inside it only
    `store_nbr` and `family` are real join keys, carried over from the sales history.
  * the demand signal behind the order quantities is real (`units` from the sales history);
    the ordering policy, the forecast error, the suppliers and the lead times are not.

Rules:
  1. supplier master     - 14 suppliers across 6 sourcing groups; every family has a primary
                           and a secondary supplier in its group, so the same family can be
                           compared across suppliers (that is what makes PPV meaningful)
  2. ordering policy     - weekly replenishment: for demand week W the planner orders
                           next-week demand x (1 + forecast error) x safety factor, rounded
                           up to the supplier's order multiple
  3. forecast error      - N(0, 15%): the planner does not know next week exactly. This error,
                           not a random stock number, is what later produces overstock and
                           out-of-stock situations in phase 8
  4. order timing        - order_date = start of demand week - the supplier's PLANNED lead time
  5. lead time           - most deliveries hit the planned lead time; a supplier-specific
                           share runs late by 1 + Poisson(sigma) days, a few arrive a day
                           early; on_time = actual receipt <= requested delivery
  6. fill rate           - supplier-specific (85-97% of lines in full); the rest arrive
                           5-30% short
  7. purchase price      - standard cost (from phase 6) x supplier price factor x +-2% noise;
                           purchase price variance = (purchase price - standard cost) x qty

Outputs (data/processed/):
  dim_supplier_sim.csv           - one row per supplier
  fact_purchase_order_sim.parquet - one row per PO line (po_id x store x family)
"""
import os
import shutil

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
LOCAL = "/tmp/procurement_layer"
os.makedirs(LOCAL, exist_ok=True)

SEED = 42
FORECAST_ERROR_SD = 0.15
SAFETY_FACTOR = 1.05
PRIMARY_SHARE = 0.70          # share of orders going to the primary supplier

# sourcing group -> families
SOURCING_GROUPS = {
    "FRESH": ["PRODUCE", "POULTRY", "MEATS", "SEAFOOD", "EGGS", "DAIRY",
              "BREAD/BAKERY", "DELI", "PREPARED FOODS"],
    "PACKAGED": ["GROCERY I", "GROCERY II", "BEVERAGES", "FROZEN FOODS", "LIQUOR,WINE,BEER"],
    "HOUSEHOLD": ["CLEANING", "HOME CARE", "PERSONAL CARE", "BEAUTY", "BABY CARE",
                  "PET SUPPLIES"],
    "HARDLINE": ["AUTOMOTIVE", "HARDWARE", "HOME APPLIANCES", "PLAYERS AND ELECTRONICS",
                 "HOME AND KITCHEN I", "HOME AND KITCHEN II", "LAWN AND GARDEN"],
    "APPAREL": ["LADIESWEAR", "LINGERIE", "CELEBRATION"],
    "MEDIA": ["BOOKS", "MAGAZINES", "SCHOOL AND OFFICE SUPPLIES"],
}

# supplier_id, name, group, planned lead time (days), lead-time sigma, late rate,
# in-full rate, price factor (vs standard cost), order multiple.
# The table encodes the classic sourcing trade-off on purpose: the cheap import vendors
# (price factor 0.93-0.96) are the unreliable ones, the dependable local suppliers charge a
# premium. Without that tension, supplier analysis has nothing to find.
SUPPLIERS = [
    ("S01", "Local Fresh Produce Co-op A",    "FRESH",      2, 1.0, 0.06, 0.97, 1.000, 10),
    ("S02", "Local Fresh Produce Co-op B",    "FRESH",      3, 1.0, 0.10, 0.94, 0.975, 10),
    ("S03", "Regional Meat & Dairy Hub",      "FRESH",      4, 2.0, 0.12, 0.95, 1.020, 25),
    ("S04", "National Packaged Goods Ltd",    "PACKAGED",   6, 2.0, 0.08, 0.96, 0.990, 50),
    ("S05", "Regional Beverage Distributor",  "PACKAGED",   5, 2.0, 0.14, 0.93, 1.015, 50),
    ("S06", "Frozen & Chilled Logistics",     "PACKAGED",   7, 3.0, 0.11, 0.95, 1.005, 25),
    ("S07", "Household Care Wholesaler",      "HOUSEHOLD",  8, 3.0, 0.09, 0.96, 0.985, 25),
    ("S08", "Personal Care Distributor",      "HOUSEHOLD",  9, 3.0, 0.16, 0.92, 1.030, 25),
    ("S09", "Import Hardline Vendor",         "HARDLINE",  16, 6.0, 0.28, 0.88, 0.960, 10),
    ("S10", "Regional Hardware Supplier",     "HARDLINE",   9, 3.0, 0.10, 0.95, 1.045, 10),
    ("S11", "Overseas Apparel Manufacturer",  "APPAREL",   21, 7.0, 0.32, 0.85, 0.930, 20),
    ("S12", "Regional Apparel Agent",         "APPAREL",   11, 4.0, 0.13, 0.94, 1.060, 20),
    ("S13", "Publishing & Stationery Dist.",  "MEDIA",      7, 2.0, 0.08, 0.96, 1.000, 20),
    ("S14", "Import Stationery Vendor",       "MEDIA",     14, 5.0, 0.24, 0.89, 0.950, 40),
]
SUPPLIER_COLUMNS = ["supplier_id", "supplier_name", "sourcing_group", "planned_lead_time_days",
                    "lead_time_sigma_days", "late_rate", "in_full_rate", "price_factor",
                    "order_multiple"]


def build_supplier_master():
    dim = pd.DataFrame(SUPPLIERS, columns=SUPPLIER_COLUMNS)
    family_rows = []
    for group, families in SOURCING_GROUPS.items():
        in_group = dim.loc[dim["sourcing_group"] == group, "supplier_id"].tolist()
        if len(in_group) < 2:
            raise SystemExit("group %s needs at least two suppliers for PPV comparison" % group)
        for i, fam in enumerate(sorted(families)):
            family_rows.append({
                "family": fam,
                "sourcing_group": group,
                "primary_supplier_id": in_group[i % len(in_group)],
                "secondary_supplier_id": in_group[(i + 1) % len(in_group)],
            })
    return dim, pd.DataFrame(family_rows)


def main():
    src = os.path.join(PROCESSED, "fact_sales_commercial.parquet")
    if not os.path.exists(src):
        raise SystemExit("run etl/phase6_simulation_layer.py first")
    df = pd.read_parquet(src, columns=["date", "store_nbr", "family", "units", "unit_cost_sim"])
    df["family"] = df["family"].astype(str)
    print("loaded:", df.shape)

    dim_supplier, family_sourcing = build_supplier_master()
    missing = sorted(set(df["family"].unique()) - set(family_sourcing["family"]))
    if missing:
        raise SystemExit("families not assigned to a sourcing group: %s" % missing)

    # ---- weekly demand per store x family (REAL signal) ----
    df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.weekday, unit="D")
    weekly = (
        df.groupby(["store_nbr", "family", "week_start"], observed=True)
          .agg(units=("units", "sum"), standard_cost=("unit_cost_sim", "mean"))
          .reset_index()
          .sort_values(["store_nbr", "family", "week_start"])
    )
    # the order placed in week t covers demand in week t+1
    weekly["demand_next_week"] = weekly.groupby(["store_nbr", "family"], observed=True)["units"].shift(-1)
    weekly["next_week_start"] = weekly["week_start"] + pd.Timedelta(days=7)
    orders = weekly.dropna(subset=["demand_next_week"]).reset_index(drop=True)
    # nothing is ordered for a family that sold nothing at all in that store that week window
    orders = orders[(orders["demand_next_week"] > 0) | (orders["units"] > 0)].reset_index(drop=True)
    print("order candidates:", len(orders))

    rng = np.random.default_rng(SEED)
    n = len(orders)

    # ---- 1. supplier choice: primary 70% / secondary 30% ----
    src_map = family_sourcing.set_index("family")
    primary = orders["family"].map(src_map["primary_supplier_id"])
    secondary = orders["family"].map(src_map["secondary_supplier_id"])
    orders["supplier_id"] = np.where(rng.random(n) < PRIMARY_SHARE, primary, secondary)

    sup = dim_supplier.set_index("supplier_id")
    planned_lt = orders["supplier_id"].map(sup["planned_lead_time_days"]).astype("int16")
    sigma = orders["supplier_id"].map(sup["lead_time_sigma_days"]).astype("float64")
    price_factor = orders["supplier_id"].map(sup["price_factor"]).astype("float64")
    multiple = orders["supplier_id"].map(sup["order_multiple"]).astype("float64")

    # ---- 2/3. ordering policy with planner forecast error ----
    forecast = orders["demand_next_week"] * (1 + rng.normal(0, FORECAST_ERROR_SD, n))
    target = np.maximum(forecast * SAFETY_FACTOR, 0.0)
    ordered = np.ceil(target / multiple) * multiple
    ordered = np.where(target <= 0, 0.0, np.maximum(ordered, multiple))

    # ---- 4/5. dates and lead time ----
    order_date = orders["next_week_start"] - pd.to_timedelta(planned_lt, unit="D")
    requested = orders["next_week_start"]
    late_rate = orders["supplier_id"].map(sup["late_rate"]).astype("float64")
    is_late = rng.random(n) < late_rate
    delay = np.where(is_late, 1 + rng.poisson(sigma), 0)
    early = np.where(~is_late & (rng.random(n) < 0.15), -1, 0)
    actual_lt = np.clip(planned_lt + delay + early, 1, 60).astype("int16")
    receipt_date = order_date + pd.to_timedelta(actual_lt, unit="D")

    # ---- 6. fill rate ----
    in_full_rate = orders["supplier_id"].map(sup["in_full_rate"]).astype("float64")
    short = rng.random(n) > in_full_rate
    fill = np.where(short, rng.uniform(0.70, 0.95, n), 1.0)
    received = np.round(ordered * fill, 2)

    # ---- 7. purchase price and price variance vs standard cost ----
    standard_cost = orders["standard_cost"].astype("float64")
    po_price = standard_cost * price_factor * (1 + rng.normal(0, 0.02, n))
    ppv_per_unit = po_price - standard_cost

    out = pd.DataFrame({
        "po_id": ("PO-" + orders["store_nbr"].astype(str).str.zfill(2) + "-"
                  + orders["supplier_id"] + "-" + order_date.dt.strftime("%Y%m%d")),
        "order_date": order_date,
        "requested_delivery_date": requested,
        "receipt_date": receipt_date,
        "store_nbr": orders["store_nbr"].astype("int16"),          # real key
        "family": orders["family"].astype("category"),             # real key
        "supplier_id": orders["supplier_id"].astype("category"),
        "planned_lead_time_days": planned_lt,
        "actual_lead_time_days": actual_lt,
        "ordered_qty": ordered.astype("float32"),
        "received_qty": received.astype("float32"),
        "standard_cost": standard_cost.astype("float32"),
        "po_unit_price": po_price.astype("float32"),
    })
    out["po_value"] = (out["ordered_qty"] * out["po_unit_price"]).astype("float32")
    out["received_value"] = (out["received_qty"] * out["po_unit_price"]).astype("float32")
    out["ppv_per_unit"] = ppv_per_unit.astype("float32")
    out["ppv_total"] = (out["ppv_per_unit"] * out["received_qty"]).astype("float32")
    out["on_time_flag"] = (out["receipt_date"] <= out["requested_delivery_date"])
    out["in_full_flag"] = (out["received_qty"] >= out["ordered_qty"] - 1e-6)

    # a week whose forecast came out at zero simply gets no purchase order - a zero-quantity
    # PO line is not a document a planner would ever raise
    dropped = int((out["ordered_qty"] <= 0).sum())
    out = out[out["ordered_qty"] > 0].reset_index(drop=True)
    print("dropped %d zero-quantity order candidates" % dropped)

    out.to_parquet(f"{LOCAL}/fact_purchase_order_sim.parquet", index=False)
    dim_supplier.merge(
        family_sourcing.groupby("primary_supplier_id").size().rename("families_primary"),
        left_on="supplier_id", right_index=True, how="left",
    ).fillna({"families_primary": 0}).to_csv(f"{LOCAL}/dim_supplier_sim.csv", index=False)
    family_sourcing.to_csv(f"{LOCAL}/dim_family_sourcing_sim.csv", index=False)
    for name in ("fact_purchase_order_sim.parquet", "dim_supplier_sim.csv",
                 "dim_family_sourcing_sim.csv"):
        shutil.copyfile(f"{LOCAL}/{name}", os.path.join(PROCESSED, name))

    # ---- summary (everything below is simulated) ----
    print("\n--- procurement scenario summary (all figures simulated; docs/20) ---")
    print("PO lines            : %d" % len(out))
    print("distinct POs        : %d" % out["po_id"].nunique())
    print("total spend         : %.0f USD" % out["po_value"].sum())
    print("purchase price var. : %+.0f USD (%.2f%% of spend)"
          % (out["ppv_total"].sum(), 100 * out["ppv_total"].sum() / out["po_value"].sum()))
    print("on-time delivery    : %.1f%%" % (100 * out["on_time_flag"].mean()))
    print("in-full delivery    : %.1f%%" % (100 * out["in_full_flag"].mean()))
    print("avg lead time       : %.1f days (planned %.1f)"
          % (out["actual_lead_time_days"].mean(), out["planned_lead_time_days"].mean()))
    perf = out.groupby("supplier_id", observed=True).agg(
        spend=("po_value", "sum"), otd=("on_time_flag", "mean"),
        infull=("in_full_flag", "mean"), ppv_pct=("ppv_per_unit", "mean"))
    perf["otd"] = (100 * perf["otd"]).round(1)
    perf["infull"] = (100 * perf["infull"]).round(1)
    print("\nsupplier performance (spend USD, OTD %%, in-full %%):\n%s"
          % perf[["spend", "otd", "infull"]].round(0).to_string())
    print("\nwritten to %s" % PROCESSED)


if __name__ == "__main__":
    main()
