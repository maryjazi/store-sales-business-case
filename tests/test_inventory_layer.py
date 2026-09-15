"""Guardrails for the derived inventory layer (phase 8).

The first duty of these tests is the audit trail: the inventory equation must close
exactly for every store x family x date, with no balancing plug anywhere. The second is
the naming contract - a shortage in this simulation must never be presented as Favorita's
historical lost sales.
"""
import os

import pandas as pd
import pytest

import audit
import schema

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
FACT = os.path.join(PROCESSED, "fact_inventory_sim.parquet")
KPI_FAMILY = os.path.join(PROCESSED, "kpi_inventory_sim.csv")

pytestmark = pytest.mark.skipif(
    not os.path.exists(FACT),
    reason="Inventory layer not generated - run etl/phase8_inventory.py first",
)

TABLE = "fact_inventory_sim.parquet"
REAL_COLUMNS = {"date", "store_nbr", "family", "observed_units"}

# Declared scenario bounds from docs/21_Inventory_Simulation.md §5.
# store-side demand fulfilment, NOT supplier OTD/in-full (those live in phase 7)
SCENARIO_FULFILLMENT_RATE_BOUNDS = (0.95, 1.00)
SCENARIO_OOS_DAY_RATE_BOUNDS = (0.005, 0.10)


@pytest.fixture(scope="module")
def inv():
    return pd.read_parquet(FACT).sort_values(["store_nbr", "family", "date"]).reset_index(drop=True)


def test_schema_is_pinned(inv):
    """The column contract lives in etl/schema.py - this checks the file against it rather
    than keeping a second copy of the column list here."""
    assert schema.validate(inv, TABLE) == []


def test_no_column_presents_a_shortage_as_lost_sales(inv):
    """Observed sales are not true demand - the dataset has neither inventory nor demand.
    A gap between observed quantity and simulated availability is a shortage of THIS supply
    chain, never Favorita's historical lost sales, and nothing may be named as if it were."""
    banned = ("lost", "missed", "forgone", "foregone")
    for col in inv.columns:
        assert not any(word in col.lower() for word in banned), col
    assert "unfulfilled_units_sim" in inv.columns


def test_inventory_lineage_passes_the_shared_audit(inv):
    """The reconciliation itself lives in etl/audit.py and is called by phase 8 before it
    writes. This test runs the SAME implementation against the persisted file, so the two
    can never drift apart. That the audit is not vacuous is proved separately, in
    tests/test_pipeline_audits.py, by feeding it deliberately broken frames."""
    audit.assert_inventory_lineage(inv)


def test_flags_match_the_quantities(inv):
    assert (inv["stockout_day_sim"] == (inv["unfulfilled_units_sim"] > 0)).all()
    assert (inv["zero_stock_day_sim"] == (inv["closing_stock"] <= 0)).all()


def test_demand_fulfillment_rate_matches_the_declared_scenario_bounds(inv):
    rate = inv["fulfilled_units_sim"].sum() / inv["observed_units"].sum()
    low, high = SCENARIO_FULFILLMENT_RATE_BOUNDS
    assert low <= rate <= high, f"simulated demand fulfillment rate {rate:.1%}"
    oos = inv["stockout_day_sim"].mean()
    low, high = SCENARIO_OOS_DAY_RATE_BOUNDS
    assert low <= oos <= high, f"simulated OOS day rate {oos:.1%}"


def test_merchandising_kpis_are_plausible():
    kpi = pd.read_csv(KPI_FAMILY)
    assert (kpi["sell_through_pct_sim"] <= 100.001).all()
    assert (kpi["simulated_demand_fulfillment_rate_pct"] <= 100.001).all()
    assert (kpi["weeks_of_supply_sim"] > 0).all()
    assert (kpi["stock_turnover_pa_sim"] > 0).all()
    assert len(kpi) == 33
