"""
Phase 13 - Commercial Cockpit Export (B8)

Builds the BI-ready model behind the commercial cockpit: a monthly star schema that both
Power BI and the Streamlit cockpit read, plus a machine-readable PROVENANCE TABLE.

WHY A PROVENANCE TABLE
----------------------
Rule P-06 (docs/19 §2) says every monetary figure must be labelled as simulated wherever it
appears - report, dashboard title, tooltip, CV bullet. Until now that rule lived in the
documentation and in review discipline. Here it becomes data: `dim_measure_provenance.csv`
maps every measure in the model to one of

    REAL                    observed in the dataset
    SIMULATED               produced by the phase-6/7 rules
    OBSERVATIONAL_ESTIMATE  estimated from real inputs against a matched baseline (B5)
    DERIVED                 arithmetic on the above, inheriting the weakest tier

The cockpit renders its labels FROM this table, so a measure cannot appear on a dashboard
without declaring what it rests on, and a test fails if one is missing.

Grain
  fact_commercial_monthly   month x store x family
  fact_procurement_monthly  month x store x family x supplier

Outputs (dashboard/commercial/)
"""
import os

import numpy as np
import pandas as pd

import schema

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
DEST = os.path.join(ROOT, "dashboard", "commercial")
LOCAL = "/tmp/cockpit_export"
os.makedirs(DEST, exist_ok=True)
os.makedirs(LOCAL, exist_ok=True)

KEYS = ["date", "store_nbr", "family"]

PROVENANCE = [
    # measure, tier, source phase, note
    ("observed_units", "REAL", 0, "units sold - a quantity, not currency (docs/19 §1)"),
    ("promo_days", "REAL", 0, "days with onpromotion > 0 - promotion occurrence"),
    ("fulfilled_units_sim", "SIMULATED", 8, "units the simulated supply chain could deliver"),
    ("unfulfilled_units_sim", "SIMULATED", 8, "shortage vs observed quantity - NOT lost sales"),
    ("revenue_sim", "SIMULATED", 9, "fulfilled units x simulated net price"),
    ("list_revenue_sim", "SIMULATED", 9, "fulfilled units x simulated list price"),
    ("markdown_value_sim", "DERIVED", 9, "list revenue - net revenue"),
    ("cogs_sim", "SIMULATED", 9, "fulfilled units x simulated unit cost"),
    ("gross_margin_sim", "DERIVED", 9, "revenue - COGS"),
    ("avg_inventory_units_sim", "SIMULATED", 8, "closing stock derived from the receipt flow"),
    ("avg_inventory_value_sim", "SIMULATED", 8, "closing stock x simulated unit cost"),
    ("stockout_days_sim", "SIMULATED", 8, "days with a shortage - a SIMULATED OOS rate"),
    ("ordered_qty_sim", "SIMULATED", 7, "purchase order quantity"),
    ("received_qty_sim", "SIMULATED", 7, "goods received"),
    ("po_value_sim", "SIMULATED", 7, "procurement spend"),
    ("ppv_total_sim", "SIMULATED", 7, "purchase price variance vs standard cost"),
    ("on_time_lines_sim", "SIMULATED", 7, "PO lines received by the requested date"),
    ("in_full_lines_sim", "SIMULATED", 7, "PO lines received in full"),
    ("avg_lead_time_days_sim", "SIMULATED", 7, "actual lead time"),
    ("estimated_observational_uplift_pct", "OBSERVATIONAL_ESTIMATE", 11,
     "promotion uplift vs a calendar-matched baseline - not causal (docs/24)"),
    ("break_even_uplift_pct_sim", "DERIVED", 10, "margin arithmetic, no behavioural assumption"),
]


def main():
    inv = schema.read_table("fact_inventory_sim.parquet", PROCESSED,
                            columns=KEYS + ["observed_units", "fulfilled_units_sim",
                                            "unfulfilled_units_sim", "closing_stock",
                                            "inventory_value_at_cost_sim", "stockout_day_sim",
                                            "fulfilled_revenue_sim", "fulfilled_cogs_sim"])
    com = schema.read_table("fact_sales_commercial.parquet", PROCESSED,
                            columns=KEYS + ["onpromotion", "list_price_sim"])
    for d in (inv, com):
        d["family"] = d["family"].astype(str)
        for c in d.columns:
            if d[c].dtype == "float32":
                d[c] = d[c].astype("float64")
    df = inv.merge(com, on=KEYS, how="inner", validate="one_to_one")
    df["month"] = df["date"].values.astype("datetime64[M]")
    df["list_revenue"] = df["fulfilled_units_sim"] * df["list_price_sim"]
    print("daily rows:", len(df))

    monthly = (df.groupby(["month", "store_nbr", "family"], observed=True)
                 .agg(observed_units=("observed_units", "sum"),
                      fulfilled_units_sim=("fulfilled_units_sim", "sum"),
                      unfulfilled_units_sim=("unfulfilled_units_sim", "sum"),
                      revenue_sim=("fulfilled_revenue_sim", "sum"),
                      list_revenue_sim=("list_revenue", "sum"),
                      cogs_sim=("fulfilled_cogs_sim", "sum"),
                      avg_inventory_units_sim=("closing_stock", "mean"),
                      avg_inventory_value_sim=("inventory_value_at_cost_sim", "mean"),
                      stockout_days_sim=("stockout_day_sim", "sum"),
                      promo_days=("onpromotion", lambda s: int((s > 0).sum())),
                      days=("observed_units", "size"))
                 .reset_index())
    monthly["markdown_value_sim"] = monthly["list_revenue_sim"] - monthly["revenue_sim"]
    monthly["gross_margin_sim"] = monthly["revenue_sim"] - monthly["cogs_sim"]
    monthly["store_nbr"] = monthly["store_nbr"].astype("int16")
    for c in ("stockout_days_sim", "promo_days", "days"):
        monthly[c] = monthly[c].astype("int32")
    monthly = monthly[["month", "store_nbr", "family", "days", "observed_units",
                       "fulfilled_units_sim", "unfulfilled_units_sim", "revenue_sim",
                       "list_revenue_sim", "markdown_value_sim", "cogs_sim", "gross_margin_sim",
                       "avg_inventory_units_sim", "avg_inventory_value_sim",
                       "stockout_days_sim", "promo_days"]]
    print("commercial monthly rows:", len(monthly))

    po = schema.read_table("fact_purchase_order_sim.parquet", PROCESSED,
                           columns=["receipt_date", "store_nbr", "family", "supplier_id",
                                    "ordered_qty", "received_qty", "po_value", "ppv_total",
                                    "actual_lead_time_days", "on_time_flag", "in_full_flag"])
    po["family"] = po["family"].astype(str)
    po["supplier_id"] = po["supplier_id"].astype(str)
    po["month"] = po["receipt_date"].values.astype("datetime64[M]")
    proc = (po.groupby(["month", "store_nbr", "family", "supplier_id"], observed=True)
              .agg(po_lines=("po_value", "size"),
                   ordered_qty_sim=("ordered_qty", "sum"),
                   received_qty_sim=("received_qty", "sum"),
                   po_value_sim=("po_value", "sum"),
                   ppv_total_sim=("ppv_total", "sum"),
                   on_time_lines_sim=("on_time_flag", "sum"),
                   in_full_lines_sim=("in_full_flag", "sum"),
                   avg_lead_time_days_sim=("actual_lead_time_days", "mean"))
              .reset_index())
    proc["store_nbr"] = proc["store_nbr"].astype("int16")
    for c in ("po_lines", "on_time_lines_sim", "in_full_lines_sim"):
        proc[c] = proc[c].astype("int32")
    for c in ("ordered_qty_sim", "received_qty_sim", "po_value_sim", "ppv_total_sim",
              "avg_lead_time_days_sim"):
        proc[c] = proc[c].astype("float64")
    print("procurement monthly rows:", len(proc))

    # ---- dimensions ----
    price_book = schema.read_table("dim_product_cost.csv", PROCESSED)
    sourcing = schema.read_table("dim_family_sourcing_sim.csv", PROCESSED)
    pricing = schema.read_table("kpi_pricing_sim.csv", PROCESSED)
    promo_econ = schema.read_table("kpi_promotion_economics_sim.csv", PROCESSED)
    dim_family = (price_book.merge(sourcing[["family", "sourcing_group",
                                             "primary_supplier_id"]], on="family")
                            .merge(pricing[["family", "gross_margin_pct_sim",
                                            "markdown_pct_sim"]], on="family")
                            .merge(promo_econ[["family", "break_even_uplift_pct_sim",
                                               "estimated_observational_uplift_pct"]],
                                   on="family", how="left"))
    dim_supplier = schema.read_table("dim_supplier_sim.csv", PROCESSED)

    provenance = pd.DataFrame(PROVENANCE, columns=["measure", "provenance_tier",
                                                   "source_phase", "note"])
    provenance["source_phase"] = provenance["source_phase"].astype("int64")

    declared = set(provenance["measure"])
    model_measures = {c for c in list(monthly.columns) + list(proc.columns)
                      if c not in ("month", "store_nbr", "family", "supplier_id", "days",
                                   "po_lines")}
    undeclared = sorted(model_measures - declared)
    if undeclared:
        raise SystemExit("measures in the model with no provenance entry: %s" % undeclared)
    print("provenance declared for %d measures, %d in the model" % (len(declared),
                                                                    len(model_measures)))

    schema.write_table(monthly, "fact_commercial_monthly.parquet", DEST, LOCAL)
    schema.write_table(proc, "fact_procurement_monthly.parquet", DEST, LOCAL)
    schema.write_table(dim_family, "dim_family_commercial.csv", DEST, LOCAL)
    schema.write_table(dim_supplier, "dim_supplier_commercial.csv", DEST, LOCAL)
    schema.write_table(provenance, "dim_measure_provenance.csv", DEST, LOCAL)

    rev = monthly["revenue_sim"].sum()
    print("\n--- cockpit model (every monetary figure simulated) ---")
    print("months            : %d (%s to %s)" % (monthly["month"].nunique(),
                                                 monthly["month"].min().date(),
                                                 monthly["month"].max().date()))
    print("simulated revenue : %.0f USD" % rev)
    print("gross margin      : %.1f%%" % (100 * monthly["gross_margin_sim"].sum() / rev))
    print("procurement spend : %.0f USD" % proc["po_value_sim"].sum())
    print("\nwritten to %s" % DEST)


if __name__ == "__main__":
    main()
