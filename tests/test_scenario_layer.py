"""Guardrails for the commercial scenario layer (phase 12).

The layer's whole claim is that it sits on the universe the pipeline already built rather
than inventing a new one. The baseline invariant is therefore the first test, and the rest
check that each lever touched exactly the families it said it would.
"""
import os

import numpy as np
import pandas as pd
import pytest

import audit
import schema

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
REPORTS = os.path.join(ROOT, "reports")
SCEN = os.path.join(PROCESSED, "kpi_commercial_scenarios_sim.csv")

pytestmark = pytest.mark.skipif(
    not os.path.exists(SCEN),
    reason="Scenario layer not generated - run etl/phase12_scenario.py first",
)

SCENARIOS = ["S0_baseline", "S1_margin_protection", "S2_availability_first",
             "S3_growth_promotion"]


@pytest.fixture(scope="module")
def scenarios():
    return schema.read_table("kpi_commercial_scenarios_sim.csv", PROCESSED)


@pytest.fixture(scope="module")
def summary():
    return schema.read_table("kpi_scenario_summary_sim.csv", PROCESSED)


def test_baseline_reproduces_the_committed_kpis(scenarios):
    pricing = schema.read_table("kpi_pricing_sim.csv", PROCESSED)
    audit.assert_scenario_baseline_matches(
        scenarios[scenarios["scenario"] == "S0_baseline"], pricing)


def test_the_baseline_audit_catches_drift(scenarios):
    pricing = schema.read_table("kpi_pricing_sim.csv", PROCESSED)
    drifted = scenarios[scenarios["scenario"] == "S0_baseline"].copy()
    drifted.loc[drifted.index[0], "revenue_sim"] *= 1.01
    with pytest.raises(audit.AuditError):
        audit.assert_scenario_baseline_matches(drifted, pricing)


def test_every_scenario_covers_the_same_families(scenarios):
    sets = {s: set(g["family"]) for s, g in scenarios.groupby("scenario")}
    assert set(sets) == set(SCENARIOS)
    assert len({frozenset(v) for v in sets.values()}) == 1


def test_baseline_pulls_no_levers(scenarios):
    base = scenarios[scenarios["scenario"] == "S0_baseline"]
    assert (base["price_change_pct"] == 0).all()


def test_scenario_arithmetic_is_internally_consistent(scenarios):
    implied_revenue = scenarios["fulfilled_units_sim"] * scenarios["net_price_sim"]
    assert ((implied_revenue - scenarios["revenue_sim"]).abs() < 1.0).all()
    implied_margin = scenarios["revenue_sim"] - scenarios["cogs_sim"]
    assert ((implied_margin - scenarios["gross_margin_sim"]).abs() < 1.0).all()
    assert (scenarios["fulfilled_units_sim"] <= scenarios["demand_units_sim"] + 1e-6).all()


def test_margin_protection_touches_only_thin_margin_families(scenarios):
    base = scenarios[scenarios["scenario"] == "S0_baseline"].set_index("family")
    margin_rate = base["gross_margin_sim"] / base["revenue_sim"]
    median = margin_rate.median()
    s1 = scenarios[scenarios["scenario"] == "S1_margin_protection"].set_index("family")
    touched = s1.index[s1["price_change_pct"] != 0]
    assert len(touched) > 0
    assert (margin_rate.loc[touched] < median).all()


def test_growth_scenario_respects_the_break_even_guard(scenarios):
    promo = schema.read_table("kpi_promotion_economics_sim.csv", PROCESSED).set_index("family")
    s3 = scenarios[scenarios["scenario"] == "S3_growth_promotion"].set_index("family")
    touched = s3.index[s3["price_change_pct"] != 0]
    assert len(touched) > 0
    gap = promo["uplift_gap_vs_break_even_pct_points"].reindex(touched)
    assert (gap > 0).all(), "a family was discounted deeper without clearing break-even"


def test_summary_changes_match_the_totals(summary):
    base = summary[summary["scenario"] == "S0_baseline"].iloc[0]
    for col in ("revenue", "gross_margin", "markdown_value", "procurement_spend",
                "avg_inventory_value"):
        implied = 100 * (summary[col + "_sim"] / base[col + "_sim"] - 1)
        assert ((implied - summary[col + "_change_vs_baseline_pct"]).abs() < 1e-6).all()


def test_nothing_is_presented_as_a_forecast(scenarios, summary):
    banned = ("forecast", "predicted", "will_", "expected_outcome")
    for df in (scenarios, summary):
        for col in df.columns:
            assert not any(word in col.lower() for word in banned), col
    assert "elasticity_assumption" in scenarios.columns


def test_the_report_states_its_limits():
    text = open(os.path.join(REPORTS, "commercial_scenarios_sim.md"), encoding="utf-8").read().lower()
    assert "never" in text
    assert "assumption, not an estimate" in text
    assert "qualification filter" in text
