"""
Shared pipeline audits.

One implementation, two callers: the ETL scripts run these before they persist anything,
and the test suite runs the SAME functions against the persisted files. That matters more
than it looks - when a test re-implements the formula it is checking, the two copies drift
and the test ends up certifying its own arithmetic instead of the pipeline's. The tests
here therefore also feed deliberately corrupted frames to these functions and assert that
they raise, so the audit itself stays honest.
"""
import numpy as np
import pandas as pd


class AuditError(Exception):
    """Raised when a reconciliation that must hold does not hold."""


GRAIN = ["store_nbr", "family"]


def _fail(name, series, atol, extra=""):
    worst = float(np.nanmax(np.abs(series))) if len(series) else 0.0
    if worst > atol or np.isnan(worst):
        raise AuditError("%s failed: max deviation %.6g (tolerance %g)%s"
                         % (name, worst, atol, extra))


def assert_inventory_lineage(df, atol=1e-3, check_carry=True):
    """The inventory chain must close with no balancing plug anywhere:

        available_t   = opening_t + receipts_t
        fulfilled_t   = min(observed_units_t, available_t)
        unfulfilled_t = observed_units_t - fulfilled_t
        closing_t     = available_t - fulfilled_t
        opening_t+1   = closing_t

    and neither stock nor shortage may be negative.
    """
    required = ["observed_units", "receipts", "opening_stock", "available",
                "fulfilled_units_sim", "unfulfilled_units_sim", "closing_stock"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise AuditError("inventory audit needs columns %s" % missing)

    _fail("available = opening + receipts",
          df["opening_stock"] + df["receipts"] - df["available"], atol)
    _fail("closing = available - fulfilled",
          df["available"] - df["fulfilled_units_sim"] - df["closing_stock"], atol)
    _fail("fulfilled = min(observed, available)",
          df[["observed_units", "available"]].min(axis=1) - df["fulfilled_units_sim"], atol)
    _fail("unfulfilled = observed - fulfilled",
          df["observed_units"] - df["fulfilled_units_sim"] - df["unfulfilled_units_sim"], atol)

    if (df["closing_stock"] < -atol).any():
        raise AuditError("negative closing stock: the equation was balanced with a plug")
    if (df["unfulfilled_units_sim"] < -atol).any():
        raise AuditError("negative shortage")

    if check_carry:
        if "date" not in df.columns:
            raise AuditError("carry-forward audit needs a date column")
        ordered = df.sort_values(GRAIN + ["date"])
        carried = ordered.groupby(GRAIN, observed=True)["closing_stock"].shift(1)
        delta = (carried - ordered["opening_stock"]).dropna()
        _fail("opening_t+1 = closing_t", delta, atol,
              " - a day's opening balance does not carry the previous day's closing balance")


def assert_revenue_views(df, atol=1.0):
    """Revenue is booked on fulfilled quantity; the demand-side view is only the potential.
    The two must differ by exactly the unfulfilled revenue - see docs/22 §2."""
    required = ["demand_revenue_sim", "revenue_sim", "unfulfilled_revenue_sim"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise AuditError("revenue audit needs columns %s" % missing)
    _fail("demand-side revenue = fulfilled + unfulfilled",
          df["demand_revenue_sim"] - df["revenue_sim"] - df["unfulfilled_revenue_sim"], atol)
    if (df["revenue_sim"] > df["demand_revenue_sim"] + atol).any():
        raise AuditError("fulfilled revenue exceeds the demand-side potential")


def assert_margin_bridge(bridge, atol=1.0):
    """Volume + price + cost must equal the margin change for every row, with no undefined
    effect. A NaN effect plus a skipna sum is how a bridge stops adding up unnoticed."""
    effects = ["volume_effect_sim", "price_effect_sim", "cost_effect_sim"]
    missing = [c for c in effects + ["margin_change_sim"] if c not in bridge.columns]
    if missing:
        raise AuditError("margin bridge audit needs columns %s" % missing)
    if bridge[effects].isna().any().any():
        raise AuditError("margin bridge contains undefined effects")
    _fail("volume + price + cost = margin change",
          bridge["margin_change_sim"] - bridge[effects].sum(axis=1, skipna=False), atol)
    if "bridge_case" in bridge.columns:
        odd = bridge[bridge["bridge_case"] == "assortment_change"]
        if len(odd) and (odd[["price_effect_sim", "cost_effect_sim"]].abs() > atol).any().any():
            raise AuditError("assortment-change rows carry a price or cost effect")


# KPI files are rounded to three decimals on write, so the cross-layer comparison below is
# defined against that rounding, not against bit equality.
CROSS_LAYER_ATOL_PER_FAMILY = 0.01
CROSS_LAYER_ATOL_TOTAL = 0.50


def assert_cross_layer_margin_consistency(inventory_kpi, pricing_kpi,
                                          per_family_atol=CROSS_LAYER_ATOL_PER_FAMILY,
                                          total_atol=CROSS_LAYER_ATOL_TOTAL):
    """Phase 8 and phase 9 compute margin, COGS and revenue on fulfilled quantity
    independently. One concept must have one value.

    This is the failure a schema contract cannot catch: both files can carry perfectly
    correct dtypes and still disagree semantically, because one layer calculated in float32
    and the other in float64.
    """
    pairs = [("fulfilled_margin", "gross_margin_sim"),
             ("fulfilled_cogs", "cogs_sim")]
    merged = inventory_kpi.merge(pricing_kpi, on="family", how="outer", indicator=True)
    if (merged["_merge"] != "both").any():
        raise AuditError("the two layers do not cover the same families")
    for inv_col, pri_col in pairs:
        if inv_col not in merged.columns or pri_col not in merged.columns:
            raise AuditError("cross-layer audit needs %s and %s" % (inv_col, pri_col))
        delta = merged[inv_col] - merged[pri_col]
        _fail("phase8.%s = phase9.%s (per family)" % (inv_col, pri_col), delta,
              per_family_atol)
        total = abs(merged[inv_col].sum() - merged[pri_col].sum())
        if total > total_atol:
            raise AuditError("phase8.%s and phase9.%s disagree by %.4f in total"
                             % (inv_col, pri_col, total))


def assert_break_even_roundtrip(be, rtol=1e-6):
    """B3-1 claims that applying the break-even volume ratio keeps gross margin flat.
    That claim is checked here rather than trusted: rebuild the margin from the ratio and
    the new price, and require the baseline back.

        units x (m/(m+x)) x (P(1+x) - C) == units x (P - C)

    Infeasible rows - where the price cut is deeper than the margin, so no volume can
    restore it - must carry no ratio at all rather than a misleading number.
    """
    required = ["baseline_units_sim", "baseline_margin_sim", "break_even_volume_ratio_sim",
                "new_price_sim", "avg_unit_cost_sim", "feasibility_flag"]
    missing = [c for c in required if c not in be.columns]
    if missing:
        raise AuditError("break-even audit needs columns %s" % missing)

    feasible = be[be["feasibility_flag"] == "feasible"]
    restored = (feasible["baseline_units_sim"] * feasible["break_even_volume_ratio_sim"]
                * (feasible["new_price_sim"] - feasible["avg_unit_cost_sim"]))
    denom = feasible["baseline_margin_sim"].abs().clip(lower=1.0)
    _fail("break-even ratio restores the baseline margin",
          (restored - feasible["baseline_margin_sim"]) / denom, rtol)

    infeasible = be[be["feasibility_flag"] != "feasible"]
    if len(infeasible) and infeasible["break_even_volume_ratio_sim"].notna().any():
        raise AuditError("rows where margin cannot be restored still carry a break-even ratio")
    if feasible["break_even_volume_ratio_sim"].isna().any():
        raise AuditError("a feasible row has no break-even ratio")


def assert_promotion_economics(e, atol=1.0):
    """Promotion economics are a comparison of two scenarios, not a hand-rolled
    decomposition:

        GM_promotion = Q1 x (P_promo - C)          (observed units at the promoted price)
        GM_baseline  = Q0 x (P_list  - C)          (baseline units at list price)
        incremental  = GM_promotion - GM_baseline

    The identity is reconstructed here so the incremental figure cannot drift away from the
    two scenarios it is supposed to be the difference of. Markdown investment and ROI are
    checked against their own definitions for the same reason.
    """
    required = ["observed_units_on_promo", "baseline_units_observational", "avg_list_price_sim",
                "avg_promo_price_sim", "avg_unit_cost_sim", "gm_promotion_scenario_sim",
                "gm_baseline_scenario_sim", "incremental_gross_margin_sim",
                "markdown_investment_sim", "promo_roi_sim"]
    missing = [c for c in required if c not in e.columns]
    if missing:
        raise AuditError("promotion economics audit needs columns %s" % missing)

    _fail("GM_promotion = Q1 x (P_promo - C)",
          e["observed_units_on_promo"] * (e["avg_promo_price_sim"] - e["avg_unit_cost_sim"])
          - e["gm_promotion_scenario_sim"], atol)
    _fail("GM_baseline = Q0 x (P_list - C)",
          e["baseline_units_observational"] * (e["avg_list_price_sim"] - e["avg_unit_cost_sim"])
          - e["gm_baseline_scenario_sim"], atol)
    _fail("incremental = GM_promotion - GM_baseline",
          e["gm_promotion_scenario_sim"] - e["gm_baseline_scenario_sim"]
          - e["incremental_gross_margin_sim"], atol)
    _fail("markdown investment = Q1 x (P_list - P_promo)",
          e["observed_units_on_promo"] * (e["avg_list_price_sim"] - e["avg_promo_price_sim"])
          - e["markdown_investment_sim"], atol)
    _fail("ROI = incremental / markdown investment",
          e["incremental_gross_margin_sim"] / e["markdown_investment_sim"] - e["promo_roi_sim"],
          1e-6)

    if any("causal" in c.lower() for c in e.columns):
        raise AuditError("a promotion column claims causality; this design cannot support it")


def assert_scenario_baseline_matches(baseline_rows, pricing_kpi, rtol=1e-6):
    """A decision layer must sit on the universe the pipeline already built. The baseline
    scenario therefore has to reproduce the committed phase-9 KPIs exactly - if it drifts,
    the layer has quietly started modelling a different business, and every comparison
    against it becomes meaningless."""
    if set(baseline_rows["family"]) != set(pricing_kpi["family"]):
        raise AuditError("the baseline scenario covers a different set of families")
    merged = baseline_rows.merge(pricing_kpi, on="family", suffixes=("_scenario", "_kpi"))
    for col in ("revenue_sim", "gross_margin_sim", "fulfilled_units_sim"):
        a_col, b_col = col + "_scenario", col + "_kpi"
        if a_col not in merged.columns or b_col not in merged.columns:
            raise AuditError("baseline audit needs %s in both frames" % col)
        denom = merged[b_col].abs().clip(lower=1.0)
        _fail("baseline %s equals the committed KPI" % col,
              (merged[a_col] - merged[b_col]) / denom, rtol)
