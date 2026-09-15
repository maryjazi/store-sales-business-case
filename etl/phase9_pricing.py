"""
Phase 9 - Pricing & Profitability (B2)

No new simulated data is created here. This phase sits on the chain the previous phases
built and turns it into commercial KPIs:

    observed units -> fulfilled units_sim -> net_price_sim -> revenue_sim
                                          -> unit_cost_sim -> cogs_sim -> gross_margin_sim

THE RECONCILIATION THIS PHASE IS BUILT AROUND
---------------------------------------------
Phase 6 priced every OBSERVED unit. Phase 8 then showed that the simulated supply chain
could not always deliver them. Booking revenue on observed units would therefore credit
the scenario with sales of goods that, inside the same scenario, were not on the shelf.

So this phase states the two views side by side and quantifies the gap:

    demand-side revenue  = observed units  x net price   (phase 6 view, potential)
    fulfilled revenue    = fulfilled units x net price   (supply-constrained, CANONICAL)
    unfulfilled revenue  = demand-side - fulfilled       (must reconcile exactly)

**From this phase onward, every commercial KPI uses the FULFILLED quantity.** The
demand-side figure is kept only as the potential against which the shortfall is measured,
and it is always labelled as such.

KPIs produced
  per family / per store : revenue, COGS, gross margin, margin %, markdown value and %,
                           price realisation %, average list and net price, and the
                           store-level price position against the chain
  margin bridge (YoY)    : exact decomposition of the gross-margin change into
                           volume, price and cost effects, computed per family so that
                           mix needs no separate residual term

Outputs (data/processed/ and reports/):
  kpi_pricing_sim.csv           - per family
  kpi_pricing_store_sim.csv     - per store
  kpi_margin_bridge_sim.csv     - per family x year pair
  reports/pricing_profitability_sim.md - readable summary
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
LOCAL = "/tmp/pricing_layer"
os.makedirs(LOCAL, exist_ok=True)

KEYS = ["date", "store_nbr", "family"]


def load():
    inv = schema.read_table("fact_inventory_sim.parquet", PROCESSED,
                            columns=KEYS + ["observed_units", "fulfilled_units_sim",
                                            "unfulfilled_units_sim", "closing_stock",
                                            "inventory_value_at_cost_sim"])
    com = schema.read_table("fact_sales_commercial.parquet", PROCESSED,
                            columns=KEYS + ["list_price_sim", "net_price_sim",
                                            "discount_pct_sim", "unit_cost_sim"])
    for d in (inv, com):
        d["family"] = d["family"].astype(str)
        for col in d.columns:
            if d[col].dtype == "float32":
                d[col] = d[col].astype("float64")   # float32 x float32 stays float32 in pandas
    df = inv.merge(com, on=KEYS, how="inner", validate="one_to_one")
    if len(df) != len(inv):
        raise SystemExit("join lost rows: %d vs %d" % (len(df), len(inv)))
    return df


def main():
    df = load()
    print("joined:", df.shape)

    # ---- the two views ----
    df["demand_revenue_sim"] = df["observed_units"] * df["net_price_sim"]
    df["revenue_sim"] = df["fulfilled_units_sim"] * df["net_price_sim"]          # canonical
    df["unfulfilled_revenue_sim"] = df["unfulfilled_units_sim"] * df["net_price_sim"]
    df["cogs_sim"] = df["fulfilled_units_sim"] * df["unit_cost_sim"]
    df["gross_margin_sim"] = df["revenue_sim"] - df["cogs_sim"]
    df["list_revenue_sim"] = df["fulfilled_units_sim"] * df["list_price_sim"]
    df["markdown_value_sim"] = df["list_revenue_sim"] - df["revenue_sim"]

    # ---- audit: one shared implementation, also used by the test suite ----
    audit.assert_revenue_views(df, atol=1e-3)
    print("revenue reconciles: demand-side = fulfilled + unfulfilled (etl/audit.py)")

    df["year"] = df["date"].dt.year

    def kpis(keys):
        g = df.groupby(keys, observed=True)
        out = g.agg(
            observed_units=("observed_units", "sum"),
            fulfilled_units_sim=("fulfilled_units_sim", "sum"),
            demand_revenue_sim=("demand_revenue_sim", "sum"),
            revenue_sim=("revenue_sim", "sum"),
            unfulfilled_revenue_sim=("unfulfilled_revenue_sim", "sum"),
            list_revenue_sim=("list_revenue_sim", "sum"),
            markdown_value_sim=("markdown_value_sim", "sum"),
            cogs_sim=("cogs_sim", "sum"),
            gross_margin_sim=("gross_margin_sim", "sum"),
            avg_inventory_value_sim=("inventory_value_at_cost_sim", "mean"),
        )
        out["gross_margin_pct_sim"] = 100 * out["gross_margin_sim"] / out["revenue_sim"]
        out["markdown_pct_sim"] = 100 * out["markdown_value_sim"] / out["list_revenue_sim"]
        out["price_realisation_pct_sim"] = 100 * out["revenue_sim"] / out["list_revenue_sim"]
        out["revenue_shortfall_pct_sim"] = (
            100 * out["unfulfilled_revenue_sim"] / out["demand_revenue_sim"])
        out["avg_list_price_sim"] = out["list_revenue_sim"] / out["fulfilled_units_sim"]
        out["avg_net_price_sim"] = out["revenue_sim"] / out["fulfilled_units_sim"]
        out["avg_unit_cost_sim"] = out["cogs_sim"] / out["fulfilled_units_sim"]
        return out.round(3).reset_index()

    kpi_family = kpis(["family"])
    kpi_store = kpis(["store_nbr"])

    # store price position: how the store's realised price compares with the chain, on the
    # same basket - a store selling cheap families cheaply is not the same as a cheap store
    chain_price = (df.groupby("family", observed=True)
                     .apply(lambda g: g["revenue_sim"].sum() / max(g["fulfilled_units_sim"].sum(), 1),
                            include_groups=False)
                     .rename("chain_avg_net_price_sim"))
    sf = (df.groupby(["store_nbr", "family"], observed=True)
            .agg(units=("fulfilled_units_sim", "sum"), revenue=("revenue_sim", "sum"))
            .reset_index().merge(chain_price, on="family", how="left"))
    sf["expected_revenue_at_chain_price"] = sf["units"] * sf["chain_avg_net_price_sim"]
    price_var = (sf.groupby("store_nbr", observed=True)
                   .apply(lambda g: 100 * (g["revenue"].sum() / g["expected_revenue_at_chain_price"].sum() - 1),
                          include_groups=False)
                   .rename("price_position_vs_chain_pct_sim").reset_index())
    kpi_store = kpi_store.merge(price_var, on="store_nbr", how="left").round(3)

    # ---- margin bridge: exact volume / price / cost decomposition, per family ----
    fy = (df.groupby(["family", "year"], observed=True)
            .agg(units=("fulfilled_units_sim", "sum"), revenue=("revenue_sim", "sum"),
                 cogs=("cogs_sim", "sum"), margin=("gross_margin_sim", "sum"))
            .reset_index())
    fy["price"] = fy["revenue"] / fy["units"].replace(0, np.nan)
    fy["cost"] = fy["cogs"] / fy["units"].replace(0, np.nan)
    prev = fy.copy()
    prev["year"] = prev["year"] + 1
    bridge = fy.merge(prev, on=["family", "year"], suffixes=("", "_prev"))
    bridge["volume_effect_sim"] = (bridge["units"] - bridge["units_prev"]) * (
        bridge["price_prev"] - bridge["cost_prev"])
    bridge["price_effect_sim"] = (bridge["price"] - bridge["price_prev"]) * bridge["units"]
    bridge["cost_effect_sim"] = -(bridge["cost"] - bridge["cost_prev"]) * bridge["units"]
    bridge["margin_change_sim"] = bridge["margin"] - bridge["margin_prev"]

    # A family that sold nothing in one of the two years has no price or cost to compare, so
    # the whole change is an assortment movement (entering or leaving the range), booked to
    # the volume effect. Without this the price and cost terms would be NaN and a skipna sum
    # would quietly drop them - which is how a bridge silently stops adding up.
    assortment = (bridge["units_prev"] <= 0) | (bridge["units"] <= 0)
    bridge.loc[assortment, ["price_effect_sim", "cost_effect_sim"]] = 0.0
    bridge.loc[assortment, "volume_effect_sim"] = bridge.loc[assortment, "margin_change_sim"]
    bridge["bridge_case"] = np.where(assortment, "assortment_change", "normal")
    print("margin bridge rows: %d normal, %d assortment change"
          % ((~assortment).sum(), assortment.sum()))

    effects = bridge[["volume_effect_sim", "price_effect_sim", "cost_effect_sim"]]
    bridge["bridge_residual"] = bridge["margin_change_sim"] - effects.sum(axis=1, skipna=False)
    audit.assert_margin_bridge(bridge, atol=1e-3)
    print("margin bridge closes: volume + price + cost = margin change (etl/audit.py)")
    bridge = bridge[["family", "year", "bridge_case", "margin_change_sim",
                     "volume_effect_sim", "price_effect_sim", "cost_effect_sim",
                     "bridge_residual"]].round(2)

    # ---- write ----
    schema.write_table(kpi_family, "kpi_pricing_sim.csv", PROCESSED, LOCAL)
    schema.write_table(kpi_store, "kpi_pricing_store_sim.csv", PROCESSED, LOCAL)
    schema.write_table(bridge, "kpi_margin_bridge_sim.csv", PROCESSED, LOCAL)

    tot = kpi_family[["demand_revenue_sim", "revenue_sim", "unfulfilled_revenue_sim",
                      "cogs_sim", "gross_margin_sim", "markdown_value_sim",
                      "list_revenue_sim"]].sum()
    lines = [
        "# Pricing & Profitability — simulated commercial scenario",
        "",
        "All monetary figures on this page are **simulated** (see `docs/19_Simulation_Design.md`).",
        "Quantities are the real observed units; what they were worth is modelled.",
        "",
        "## 1. Which quantity carries the revenue",
        "",
        "| View | Units | Revenue (simulated) |",
        "|---|---|---|",
        "| Demand-side (observed units, phase 6) | %.0f | %.0f USD |" % (
            kpi_family["observed_units"].sum(), tot["demand_revenue_sim"]),
        "| **Fulfilled (canonical from B2 onward)** | %.0f | **%.0f USD** |" % (
            kpi_family["fulfilled_units_sim"].sum(), tot["revenue_sim"]),
        "| Shortfall — could not be served in this scenario | %.0f | %.0f USD (%.2f%%) |" % (
            kpi_family["observed_units"].sum() - kpi_family["fulfilled_units_sim"].sum(),
            tot["unfulfilled_revenue_sim"],
            100 * tot["unfulfilled_revenue_sim"] / tot["demand_revenue_sim"]),
        "",
        "Revenue is booked on **fulfilled** quantity. Booking it on observed units would credit",
        "the scenario with goods that, inside the same scenario, were not on the shelf. The",
        "shortfall is a limitation of this simulated supply chain, not Favorita's lost sales.",
        "",
        "## 2. Headline profitability (simulated)",
        "",
        "| KPI | Value |",
        "|---|---|",
        "| Revenue at list price | %.0f USD |" % tot["list_revenue_sim"],
        "| Markdown given away | %.0f USD (%.1f%% of list) |" % (
            tot["markdown_value_sim"], 100 * tot["markdown_value_sim"] / tot["list_revenue_sim"]),
        "| Net revenue | %.0f USD |" % tot["revenue_sim"],
        "| COGS | %.0f USD |" % tot["cogs_sim"],
        "| Gross margin | %.0f USD (%.1f%%) |" % (
            tot["gross_margin_sim"], 100 * tot["gross_margin_sim"] / tot["revenue_sim"]),
        "",
        "## 3. Margin extremes by family (simulated)",
        "",
        kpi_family.nlargest(5, "gross_margin_pct_sim")[
            ["family", "gross_margin_pct_sim", "markdown_pct_sim", "revenue_sim"]].to_markdown(index=False),
        "",
        kpi_family.nsmallest(5, "gross_margin_pct_sim")[
            ["family", "gross_margin_pct_sim", "markdown_pct_sim", "revenue_sim"]].to_markdown(index=False),
        "",
        "## 4. Margin bridge",
        "",
        "The year-on-year change in gross margin, split into volume, price and cost effects.",
        "The decomposition is computed per family and summed, so it closes exactly and needs no",
        "residual mix term. Full table: `data/processed/kpi_margin_bridge_sim.csv`.",
        "",
    ]
    tot_bridge = (bridge.groupby("year")[["margin_change_sim", "volume_effect_sim",
                                          "price_effect_sim", "cost_effect_sim"]].sum().round(0))
    lines.append(tot_bridge.to_markdown())
    lines.append("")
    with open(f"{LOCAL}/pricing_profitability_sim.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    shutil.copyfile(f"{LOCAL}/pricing_profitability_sim.md",
                    os.path.join(REPORTS, "pricing_profitability_sim.md"))

    print("\n--- pricing scenario summary (all monetary figures simulated) ---")
    print("demand-side revenue : %.0f USD" % tot["demand_revenue_sim"])
    print("fulfilled revenue   : %.0f USD  <- canonical from B2 onward" % tot["revenue_sim"])
    print("revenue shortfall   : %.0f USD (%.2f%%)" % (
        tot["unfulfilled_revenue_sim"],
        100 * tot["unfulfilled_revenue_sim"] / tot["demand_revenue_sim"]))
    print("markdown given away : %.0f USD (%.1f%% of list revenue)" % (
        tot["markdown_value_sim"], 100 * tot["markdown_value_sim"] / tot["list_revenue_sim"]))
    print("gross margin        : %.0f USD (%.1f%%)" % (
        tot["gross_margin_sim"], 100 * tot["gross_margin_sim"] / tot["revenue_sim"]))
    print("\nwritten to %s and reports/" % PROCESSED)


if __name__ == "__main__":
    main()
