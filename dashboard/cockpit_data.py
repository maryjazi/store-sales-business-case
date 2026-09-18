"""
Data layer for the commercial cockpit (B8).

Kept free of Streamlit on purpose: the loading, the KPI arithmetic and - most importantly -
the provenance labelling are plain functions, so the test suite can check them without a
browser. The cockpit itself is only the drawing on top.

PROVENANCE LABELS ARE NOT WRITTEN BY HAND. `label_for()` reads
`dashboard/commercial/dim_measure_provenance.csv` and derives the suffix from the declared
tier. A measure that is not declared raises, so a figure cannot reach a dashboard without
saying what it rests on (rule P-06, docs/19 §2).
"""
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "commercial")

TIER_SUFFIX = {
    "REAL": "",
    "SIMULATED": " (simulated)",
    "DERIVED": " (simulated)",
    "OBSERVATIONAL_ESTIMATE": " (observational estimate)",
}


class ProvenanceError(Exception):
    """Raised when a measure would be displayed without a declared provenance tier."""


def load_model():
    """The five tables of the cockpit model, as written by etl/phase13_commercial_export.py."""
    fact = pd.read_parquet(os.path.join(MODEL, "fact_commercial_monthly.parquet"))
    proc = pd.read_parquet(os.path.join(MODEL, "fact_procurement_monthly.parquet"))
    families = pd.read_csv(os.path.join(MODEL, "dim_family_commercial.csv"))
    suppliers = pd.read_csv(os.path.join(MODEL, "dim_supplier_commercial.csv"))
    provenance = pd.read_csv(os.path.join(MODEL, "dim_measure_provenance.csv"))
    return fact, proc, families, suppliers, provenance


def label_for(measure, title, provenance):
    """Title plus the suffix its declared provenance tier requires."""
    row = provenance.loc[provenance["measure"] == measure]
    if row.empty:
        raise ProvenanceError(
            "%s has no provenance entry - declare it in phase13 before displaying it" % measure)
    tier = row.iloc[0]["provenance_tier"]
    if tier not in TIER_SUFFIX:
        raise ProvenanceError("%s declares an unknown tier %r" % (measure, tier))
    return title + TIER_SUFFIX[tier]


def executive_kpis(fact, proc):
    """The headline set, as ratios of sums (never means of ratios - see docs/24 §2)."""
    revenue = fact["revenue_sim"].sum()
    return {
        "revenue_sim": revenue,
        "gross_margin_sim": fact["gross_margin_sim"].sum(),
        "gross_margin_pct": 100 * fact["gross_margin_sim"].sum() / revenue,
        "markdown_pct": 100 * fact["markdown_value_sim"].sum() / fact["list_revenue_sim"].sum(),
        "po_value_sim": proc["po_value_sim"].sum(),
        "fulfillment_pct": 100 * fact["fulfilled_units_sim"].sum() / fact["observed_units"].sum(),
        "oos_day_rate_pct": 100 * fact["stockout_days_sim"].sum() / fact["days"].sum(),
    }


def by_month(fact):
    m = fact.groupby("month", as_index=False)[
        ["revenue_sim", "gross_margin_sim", "markdown_value_sim", "list_revenue_sim",
         "avg_inventory_value_sim"]].sum()
    m["gross_margin_pct"] = 100 * m["gross_margin_sim"] / m["revenue_sim"]
    m["markdown_pct"] = 100 * m["markdown_value_sim"] / m["list_revenue_sim"]
    return m


def by_family(fact, families):
    f = fact.groupby("family", as_index=False)[
        ["revenue_sim", "gross_margin_sim", "markdown_value_sim", "list_revenue_sim",
         "observed_units", "fulfilled_units_sim", "unfulfilled_units_sim",
         "avg_inventory_value_sim", "stockout_days_sim", "days"]].sum()
    f["gross_margin_pct"] = 100 * f["gross_margin_sim"] / f["revenue_sim"]
    f["markdown_pct"] = 100 * f["markdown_value_sim"] / f["list_revenue_sim"]
    f["oos_day_rate_pct"] = 100 * f["stockout_days_sim"] / f["days"]
    f["fulfillment_pct"] = 100 * f["fulfilled_units_sim"] / f["observed_units"]
    return f.merge(families, on="family", how="left")


def by_supplier(proc, suppliers):
    s = proc.groupby("supplier_id", as_index=False)[
        ["po_value_sim", "ordered_qty_sim", "received_qty_sim", "ppv_total_sim",
         "on_time_lines_sim", "in_full_lines_sim", "po_lines"]].sum()
    s["on_time_pct"] = 100 * s["on_time_lines_sim"] / s["po_lines"]
    s["in_full_pct"] = 100 * s["in_full_lines_sim"] / s["po_lines"]
    s["ppv_pct_of_spend"] = 100 * s["ppv_total_sim"] / s["po_value_sim"]
    lead = proc.groupby("supplier_id", as_index=False)["avg_lead_time_days_sim"].mean()
    return s.merge(lead, on="supplier_id").merge(suppliers, on="supplier_id", how="left")
