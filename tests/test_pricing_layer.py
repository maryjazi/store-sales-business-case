"""Guardrails for the pricing & profitability layer (phase 9).

The centre of this phase is a reconciliation, so that is what the tests protect: revenue
must be booked on the quantity the simulated supply chain could actually deliver, the gap
to the demand-side view must be explicit, and the margin bridge must close exactly.
"""
import os

import pandas as pd
import pytest

import audit
import schema

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
KPI = os.path.join(PROCESSED, "kpi_pricing_sim.csv")
KPI_STORE = os.path.join(PROCESSED, "kpi_pricing_store_sim.csv")
BRIDGE = os.path.join(PROCESSED, "kpi_margin_bridge_sim.csv")

pytestmark = pytest.mark.skipif(
    not os.path.exists(KPI),
    reason="Pricing layer not generated - run etl/phase9_pricing.py first",
)

# Declared scenario bounds (docs/22 §5). Same convention as docs/19-21: these describe
# this scenario, not the retail sector and not the dataset.
SCENARIO_MARGIN_PCT_BOUNDS = (20.0, 28.0)
SCENARIO_MARKDOWN_PCT_BOUNDS = (2.0, 20.0)

REAL_OR_AUDIT_COLUMNS = {"family", "store_nbr", "year", "observed_units", "bridge_case",
                         "bridge_residual"}


@pytest.fixture(scope="module")
def kpi():
    return pd.read_csv(KPI)


@pytest.fixture(scope="module")
def bridge():
    return pd.read_csv(BRIDGE)


def test_every_modelled_column_is_marked_simulated(kpi):
    for path in (KPI, KPI_STORE, BRIDGE):
        for col in pd.read_csv(path, nrows=1).columns:
            if col not in REAL_OR_AUDIT_COLUMNS:
                assert col.endswith("_sim"), f"{os.path.basename(path)}: {col}"


def test_revenue_views_pass_the_shared_audit(kpi):
    """Same implementation phase 9 runs before it writes (etl/audit.py)."""
    audit.assert_revenue_views(kpi)


def test_revenue_is_booked_on_fulfilled_quantity(kpi):
    """Booking revenue on observed units would credit the scenario with goods that, inside
    the same scenario, were never on the shelf."""
    assert (kpi["fulfilled_units_sim"] <= kpi["observed_units"] + 1e-6).all()
    assert (kpi["revenue_sim"] <= kpi["demand_revenue_sim"] + 1e-6).all()
    assert kpi["unfulfilled_revenue_sim"].sum() > 0, "a scenario with no shortfall at all"


def test_margin_and_markdown_are_internally_consistent(kpi):
    implied = kpi["revenue_sim"] - kpi["cogs_sim"]
    assert ((implied - kpi["gross_margin_sim"]).abs() < 1.0).all()
    implied_markdown = kpi["list_revenue_sim"] - kpi["revenue_sim"]
    assert ((implied_markdown - kpi["markdown_value_sim"]).abs() < 1.0).all()
    realisation = kpi["price_realisation_pct_sim"] + kpi["markdown_pct_sim"]
    assert ((realisation - 100).abs() < 0.01).all()


def test_chain_margin_and_markdown_match_the_declared_scenario_bounds(kpi):
    margin_pct = 100 * kpi["gross_margin_sim"].sum() / kpi["revenue_sim"].sum()
    low, high = SCENARIO_MARGIN_PCT_BOUNDS
    assert low <= margin_pct <= high, f"chain margin {margin_pct:.1f}%"
    markdown_pct = 100 * kpi["markdown_value_sim"].sum() / kpi["list_revenue_sim"].sum()
    low, high = SCENARIO_MARKDOWN_PCT_BOUNDS
    assert low <= markdown_pct <= high, f"chain markdown {markdown_pct:.1f}%"


def test_margin_bridge_passes_the_shared_audit(bridge):
    audit.assert_margin_bridge(bridge)
    assert bridge["bridge_residual"].abs().max() < 1.0


def test_bridge_labels_assortment_changes_explicitly(bridge):
    assert set(bridge["bridge_case"]) <= {"normal", "assortment_change"}
    odd = bridge[bridge["bridge_case"] == "assortment_change"]
    assert (odd["price_effect_sim"] == 0).all()
    assert (odd["cost_effect_sim"] == 0).all()


def test_store_price_position_is_centred_on_the_chain():
    store = pd.read_csv(KPI_STORE)
    assert len(store) == 54
    assert store["price_position_vs_chain_pct_sim"].abs().max() < 15
    assert store["price_position_vs_chain_pct_sim"].std() > 0
