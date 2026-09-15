"""Guardrails for the price sensitivity layer (phase 10).

Two things are protected. First the arithmetic: the break-even ratio must genuinely restore
the baseline margin, and no scenario row may disappear because it was inconvenient. Second
the framing: this phase must never present an elasticity estimate, and the diagnostic
regression that exists to demonstrate why must stay out of the KPI outputs.
"""
import os

import numpy as np
import pandas as pd
import pytest

import audit
import schema

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
BE = os.path.join(PROCESSED, "kpi_break_even_elasticity_sim.csv")

pytestmark = pytest.mark.skipif(
    not os.path.exists(BE),
    reason="Price sensitivity layer not generated - run etl/phase10_price_sensitivity.py",
)

PRICE_STEPS = 10
ELASTICITY_ASSUMPTIONS = 3
FAMILIES = 33


@pytest.fixture(scope="module")
def be():
    return schema.read_table("kpi_break_even_elasticity_sim.csv", PROCESSED)


@pytest.fixture(scope="module")
def grid():
    return schema.read_table("kpi_price_scenario_sim.csv", PROCESSED)


def test_break_even_passes_the_shared_audit(be):
    audit.assert_break_even_roundtrip(be)


def test_the_break_even_audit_catches_a_wrong_ratio(be):
    broken = be.copy()
    idx = broken.index[broken["feasibility_flag"] == "feasible"][0]
    broken.loc[idx, "break_even_volume_ratio_sim"] *= 1.05
    with pytest.raises(audit.AuditError):
        audit.assert_break_even_roundtrip(broken)


def test_no_row_is_silently_dropped(be, grid):
    assert len(be) == FAMILIES * PRICE_STEPS
    assert len(grid) == FAMILIES * PRICE_STEPS * ELASTICITY_ASSUMPTIONS
    assert be["price_change_pct"].nunique() == PRICE_STEPS
    assert grid["elasticity_assumption"].nunique() == ELASTICITY_ASSUMPTIONS


def test_unrestorable_rows_carry_no_misleading_ratio(be):
    bad = be[be["feasibility_flag"] != "feasible"]
    assert bad["break_even_volume_ratio_sim"].isna().all()
    # a price cut deeper than the margin is exactly when margin cannot be restored
    assert (bad["margin_rate_sim"] + bad["price_change_pct"] / 100 <= 0).all()


def test_below_cost_rows_are_flagged_and_kept(be, grid):
    for df in (be, grid):
        expected = df["new_price_sim"] <= (
            df["avg_unit_cost_sim"] if "avg_unit_cost_sim" in df.columns
            else df["new_cogs_sim"] / df["new_units_sim"])
        assert (df["below_cost_flag"] == expected).all()


def test_scenario_volume_follows_the_declared_functional_form(grid):
    expected = (1 + grid["price_change_pct"] / 100) ** grid["elasticity_assumption"]
    assert ((expected - grid["volume_ratio_sim"]).abs() < 1e-9).all()


def test_scenario_margin_change_is_consistent(grid):
    implied = 100 * (grid["new_margin_sim"] / grid["baseline_margin_sim"] - 1)
    assert ((implied - grid["margin_change_vs_baseline_pct"]).abs() < 1e-6).all()
    implied_margin = grid["new_revenue_sim"] - grid["new_cogs_sim"]
    assert ((implied_margin - grid["new_margin_sim"]).abs() < 1e-6).all()


def test_the_revenue_margin_tradeoff_actually_exists(grid):
    """The decision this phase supports is revenue against margin; if no row ever moved the
    two in opposite directions, the grid would not be telling a pricing analyst anything."""
    opposed = grid[(grid["revenue_change_vs_baseline_pct"] < 0)
                   & (grid["margin_change_vs_baseline_pct"] > 0)]
    assert len(opposed) > 0


def test_no_kpi_output_carries_an_elasticity_estimate():
    """B3-3 is a methodological demonstration, not a finding. Its regression must not leak
    into the KPI outputs, however plausible the coefficients look."""
    for name in ("kpi_break_even_elasticity_sim.csv", "kpi_price_scenario_sim.csv"):
        cols = list(schema.SCHEMAS[name]["columns"])
        assert "log_log_slope" not in cols
        assert not any("estimate" in c.lower() for c in cols)
    diagnostic = schema.read_table("diagnostic_price_volume_regression_sim.csv", PROCESSED)
    assert "interpretation_warning" in diagnostic.columns
    assert diagnostic["interpretation_warning"].str.contains("NOT an elasticity").all()


def test_the_diagnostic_is_declared_as_a_method_demonstration():
    """The guardrail is about what the coefficient IS, not about what value it takes.

    A previous version asserted that some slopes come out positive, because in this run they
    do (+8.6) and it makes the point vividly. That was the wrong contract: if upstream data
    or scenario rules legitimately changed and every slope turned negative, the guardrail
    would still hold - the number is not a causal elasticity either way. So the test pins the
    methodology instead of reproducing a result.
    """
    name = "diagnostic_price_volume_regression_sim.csv"
    diagnostic = schema.read_table(name, PROCESSED)

    assert name.startswith("diagnostic_") and name.endswith("_sim.csv")
    assert schema.SCHEMAS[name]["phase"] == 10
    assert not any(word in c.lower() for c in diagnostic.columns
                   for word in ("estimate", "elasticity", "causal"))

    assert np.isfinite(diagnostic["log_log_slope"]).all()
    assert np.isfinite(diagnostic["r_squared"]).all()
    assert diagnostic["r_squared"].between(0, 1).all()
    assert (diagnostic["n_rows"] > 1000).all(), "too few observations to be worth showing"
    assert len(diagnostic) == FAMILIES
