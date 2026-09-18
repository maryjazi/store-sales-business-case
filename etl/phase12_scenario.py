"""
Phase 12 - Commercial Scenario Analysis (B7)

This phase builds NO new simulation universe. It is a decision layer on top of the one the
earlier phases already produced: pricing (B2), break-even (B3), inventory (B4), procurement
(B6) and promotion (B5) are connected to a small set of policy levers, and every scenario is
scored on the SAME KPI set.

    Revenue . Gross margin . Markdown . Procurement spend . Fulfilment . Inventory . OOS

THE ANCHOR
----------
Scenario S0 is the baseline, and it must reproduce the committed KPIs of phases 8 and 9
exactly - `audit.assert_scenario_baseline_matches` checks it against the persisted files.
If the baseline drifts, the decision layer has started inventing its own universe instead of
sitting on the existing one, and the phase fails rather than reporting.

THE LEVERS (each one an explicit, documented assumption)
-------------------------------------------------------
S1 Margin Protection  halve the discount on families whose margin rate is below the chain
                      median - the families where B3 showed a discount can barely pay for
                      itself.
S2 Availability First re-source the most out-of-stock-prone quartile to the more reliable
                      supplier in their group: higher purchase price, better fill rate.
S3 Growth/Promotion   deepen the discount by 5 points, but ONLY on families whose estimated
                      observational uplift already exceeded their break-even requirement
                      (B5-4). That is the break-even guard.

RESPONSE FUNCTIONS
------------------
Price changes move volume through the stated elasticity assumption of B3-2 (default -1.5,
constant-elasticity form). The observational uplift estimate from B5 is used ONLY as a
qualification filter for S3 - never as a response function, because it is an association
under a calendar-matched baseline, not a causal coefficient.

Volume moves demand; demand moves the shortfall, inventory and procurement spend through the
simple proportional mappings documented in docs/25. They are deliberately transparent: a
decision layer whose mechanics cannot be explained in two lines is not a decision aid.

Outputs:
  data/processed/kpi_commercial_scenarios_sim.csv   - scenario x family
  data/processed/kpi_scenario_summary_sim.csv       - scenario totals on the common KPI set
  reports/commercial_scenarios_sim.md
"""
import os
import shutil

import numpy as np
import pandas as pd

import audit
import schema

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
REPORTS = os.path.join(ROOT, "reports")
LOCAL = "/tmp/scenario_layer"
os.makedirs(LOCAL, exist_ok=True)

ELASTICITY_ASSUMPTION = -1.5          # from the stated set in docs/23 §3
S1_DISCOUNT_FACTOR = 0.5              # halve the discount
S3_EXTRA_DISCOUNT_PTS = 5.0           # deepen by 5 percentage points
S2_OOS_QUARTILE = 0.75


def baseline_frame():
    pricing = schema.read_table("kpi_pricing_sim.csv", PROCESSED)
    inventory = schema.read_table("kpi_inventory_sim.csv", PROCESSED)
    promo = schema.read_table("kpi_promotion_economics_sim.csv", PROCESSED)
    po = schema.read_table("fact_purchase_order_sim.parquet", PROCESSED,
                           columns=["family", "ordered_qty", "po_value"])
    supplier = schema.read_table("dim_supplier_sim.csv", PROCESSED)
    sourcing = schema.read_table("dim_family_sourcing_sim.csv", PROCESSED)

    po_family = po.groupby("family", observed=True).agg(
        ordered_qty=("ordered_qty", "sum"), po_value=("po_value", "sum")).reset_index()
    po_family["po_unit_price"] = po_family["po_value"] / po_family["ordered_qty"]

    b = pricing[["family", "observed_units", "fulfilled_units_sim", "revenue_sim", "cogs_sim",
                 "gross_margin_sim", "markdown_value_sim", "list_revenue_sim"]].copy()
    b = b.merge(inventory[["family", "avg_inventory_value", "simulated_oos_day_rate_pct",
                           "simulated_demand_fulfillment_rate_pct"]], on="family")
    b = b.merge(po_family[["family", "ordered_qty", "po_value", "po_unit_price"]], on="family")
    b = b.merge(promo[["family", "uplift_gap_vs_break_even_pct_points"]], on="family", how="left")

    b["net_price"] = b["revenue_sim"] / b["fulfilled_units_sim"]
    b["list_price"] = b["list_revenue_sim"] / b["fulfilled_units_sim"]
    b["unit_cost"] = b["cogs_sim"] / b["fulfilled_units_sim"]
    b["discount_pct"] = 100 * (1 - b["net_price"] / b["list_price"])
    b["margin_rate"] = b["gross_margin_sim"] / b["revenue_sim"]
    b["shortfall_rate"] = 1 - b["fulfilled_units_sim"] / b["observed_units"]

    # the more reliable partner inside the family's own sourcing group, and what it costs
    sup = supplier.set_index("supplier_id")
    s = sourcing.merge(b[["family"]], on="family")
    best, factor = [], []
    for row in s.itertuples():
        options = sup.loc[[row.primary_supplier_id, row.secondary_supplier_id]]
        pick = options["late_rate"].idxmin()
        best.append(pick)
        factor.append(options.loc[pick, "price_factor"]
                      / options.loc[row.primary_supplier_id, "price_factor"])
    s["reliable_supplier_id"] = best
    s["reliable_price_uplift"] = factor
    s["reliable_in_full"] = sup.loc[s["reliable_supplier_id"], "in_full_rate"].to_numpy()
    s["current_in_full"] = sup.loc[s["primary_supplier_id"], "in_full_rate"].to_numpy()
    return b.merge(s[["family", "reliable_supplier_id", "reliable_price_uplift",
                      "reliable_in_full", "current_in_full"]], on="family")


def score(b, name, description, price_change_pct, cost_factor, shortfall_factor):
    """Apply the levers and score the scenario on the common KPI set."""
    x = price_change_pct / 100.0
    volume_ratio = np.where(x == 0, 1.0, (1 + x) ** ELASTICITY_ASSUMPTION)

    demand = b["observed_units"] * volume_ratio
    shortfall_rate = np.clip(b["shortfall_rate"] * shortfall_factor, 0, 1)
    fulfilled = demand * (1 - shortfall_rate)
    net_price = b["net_price"] * (1 + x)
    unit_cost = b["unit_cost"] * cost_factor

    out = pd.DataFrame({
        "scenario": name,
        "scenario_description": description,
        "family": b["family"],
        "elasticity_assumption": ELASTICITY_ASSUMPTION,
        "price_change_pct": price_change_pct,
        "demand_units_sim": demand,
        "fulfilled_units_sim": fulfilled,
        "net_price_sim": net_price,
        "unit_cost_sim": unit_cost,
    })
    out["revenue_sim"] = out["fulfilled_units_sim"] * out["net_price_sim"]
    out["cogs_sim"] = out["fulfilled_units_sim"] * out["unit_cost_sim"]
    out["gross_margin_sim"] = out["revenue_sim"] - out["cogs_sim"]
    out["markdown_value_sim"] = out["fulfilled_units_sim"] * (b["list_price"] - out["net_price_sim"])
    out["procurement_spend_sim"] = (b["ordered_qty"] * (demand / b["observed_units"])
                                    * b["po_unit_price"] * cost_factor)
    out["avg_inventory_value_sim"] = b["avg_inventory_value"] * (demand / b["observed_units"])
    out["demand_fulfillment_rate_pct_sim"] = 100 * (1 - shortfall_rate)
    out["simulated_oos_day_rate_pct"] = (b["simulated_oos_day_rate_pct"]
                                         * (shortfall_rate / b["shortfall_rate"].replace(0, np.nan))
                                         ).fillna(b["simulated_oos_day_rate_pct"])
    return out


def main():
    b = baseline_frame()
    print("baseline families:", len(b))
    median_margin = b["margin_rate"].median()
    oos_cut = b["simulated_oos_day_rate_pct"].quantile(S2_OOS_QUARTILE)

    # ---- S1: halve the discount where the margin is thin ----
    thin = b["margin_rate"] < median_margin
    s1_price = np.where(thin, b["discount_pct"] * S1_DISCOUNT_FACTOR / (100 - b["discount_pct"]) * 100, 0.0)

    # ---- S2: re-source the OOS-prone quartile to the more reliable supplier ----
    prone = b["simulated_oos_day_rate_pct"] >= oos_cut
    s2_cost = np.where(prone, b["reliable_price_uplift"], 1.0)
    improvement = np.where(prone,
                           1 - np.clip((1 - b["reliable_in_full"]) / (1 - b["current_in_full"]), 0, 1),
                           0.0)
    s2_shortfall = 1 - improvement

    # ---- S3: deepen the discount only where the break-even guard is cleared ----
    qualifies = b["uplift_gap_vs_break_even_pct_points"].fillna(-np.inf) > 0
    s3_price = np.where(qualifies, -S3_EXTRA_DISCOUNT_PTS, 0.0)

    scenarios = pd.concat([
        score(b, "S0_baseline", "current policy", 0.0, 1.0, 1.0),
        score(b, "S1_margin_protection",
              "halve the discount on families with a below-median margin rate", s1_price, 1.0, 1.0),
        score(b, "S2_availability_first",
              "re-source the most OOS-prone quartile to the more reliable supplier", 0.0,
              s2_cost, s2_shortfall),
        score(b, "S3_growth_promotion",
              "deepen the discount by 5 points where estimated uplift cleared break-even",
              s3_price, 1.0, 1.0),
    ], ignore_index=True)
    scenarios["families_touched_by_lever"] = scenarios["price_change_pct"].ne(0) | \
        scenarios["unit_cost_sim"].ne(scenarios.groupby("family")["unit_cost_sim"].transform("first"))

    audit.assert_scenario_baseline_matches(
        scenarios[scenarios["scenario"] == "S0_baseline"],
        schema.read_table("kpi_pricing_sim.csv", PROCESSED))
    print("baseline scenario reproduces the committed phase-9 KPIs exactly (etl/audit.py)")

    kpis = ["revenue_sim", "gross_margin_sim", "markdown_value_sim", "procurement_spend_sim",
            "avg_inventory_value_sim", "fulfilled_units_sim", "demand_units_sim"]
    summary = scenarios.groupby(["scenario", "scenario_description"], observed=True)[kpis].sum()
    summary["gross_margin_pct_sim"] = 100 * summary["gross_margin_sim"] / summary["revenue_sim"]
    summary["demand_fulfillment_rate_pct_sim"] = (
        100 * summary["fulfilled_units_sim"] / summary["demand_units_sim"])
    summary["oos_day_rate_pct_sim"] = scenarios.groupby("scenario", observed=True).apply(
        lambda g: np.average(g["simulated_oos_day_rate_pct"],
                             weights=g["demand_units_sim"]), include_groups=False).to_numpy()
    summary["families_touched"] = [
        int(((scenarios["scenario"] == s) & scenarios["families_touched_by_lever"]).sum())
        for s in summary.index.get_level_values(0)]
    base = summary.loc["S0_baseline"].iloc[0]
    for col in ("revenue_sim", "gross_margin_sim", "markdown_value_sim",
                "procurement_spend_sim", "avg_inventory_value_sim"):
        summary[col.replace("_sim", "") + "_change_vs_baseline_pct"] = (
            100 * (summary[col] / base[col] - 1))
    summary = summary.reset_index()

    schema.write_table(scenarios.drop(columns=["families_touched_by_lever"]),
                       "kpi_commercial_scenarios_sim.csv", PROCESSED, LOCAL)
    schema.write_table(summary, "kpi_scenario_summary_sim.csv", PROCESSED, LOCAL)

    show = ["scenario", "revenue_change_vs_baseline_pct", "gross_margin_change_vs_baseline_pct",
            "markdown_value_change_vs_baseline_pct", "procurement_spend_change_vs_baseline_pct",
            "avg_inventory_value_change_vs_baseline_pct", "demand_fulfillment_rate_pct_sim",
            "oos_day_rate_pct_sim"]
    lines = [
        "# Commercial Scenarios — a decision layer, not a new simulation",
        "",
        "Every figure is **simulated** (`docs/19`). This page changes no data: it applies policy",
        "levers to the universe phases 6–11 already built and scores each scenario on one common",
        "KPI set. Scenario **S0 reproduces the committed phase-9 KPIs exactly** — an audit fails",
        "the phase if it does not, because a decision layer that drifts from its own baseline is",
        "no longer describing the same business.",
        "",
        "| Scenario | Lever | Families touched |",
        "|---|---|---|",
    ]
    for r in summary.itertuples():
        lines.append("| `%s` | %s | %d |" % (r.scenario, r.scenario_description, r.families_touched))
    lines += [
        "",
        "## Scored on the common KPI set",
        "",
        "Changes against baseline, in percent:",
        "",
        summary[show].round(2).to_markdown(index=False),
        "",
        "## How to read this",
        "",
        "Volume responds to price through the **stated elasticity assumption** of docs/23 §3",
        "(%.1f, constant-elasticity form). It is an assumption, not an estimate." % ELASTICITY_ASSUMPTION,
        "",
        "The observational uplift from B5 is used **only as a qualification filter** in S3 —",
        "which families are allowed a deeper discount — and never as a response function. It is",
        "an association under a calendar-matched baseline, not a causal coefficient, and the",
        "placebo test in docs/24 §3 is the reason that distinction is kept.",
        "",
        "Inventory, procurement spend and shortfall follow proportional mappings documented in",
        "`docs/25_Scenario_Design.md` §4. They are deliberately transparent rather than clever:",
        "a decision layer whose mechanics cannot be explained in two lines is not a decision aid.",
        "",
        "## What this does not tell you",
        "",
        "- **Never**: that a scenario *will* deliver these numbers. Each one is a policy applied",
        "  to a simulated commercial layer under a stated elasticity assumption.",
        "- **Never**: that S3 is profitable because uplift cleared break-even in B5 — that gate",
        "  is observational, and it selects families rather than predicting their response.",
        "",
    ]
    path = os.path.join(LOCAL, "commercial_scenarios_sim.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    shutil.copyfile(path, os.path.join(REPORTS, "commercial_scenarios_sim.md"))

    print("\n--- scenario summary (change vs baseline) ---")
    print(summary[show].round(2).to_string(index=False))
    print("\nwritten to %s and reports/" % PROCESSED)


if __name__ == "__main__":
    main()
