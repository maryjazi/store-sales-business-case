"""Guardrails for the simulated procurement layer (phase 7).

Two things are protected here:
  1. internal consistency - a receipt cannot precede its order, a delivery cannot exceed
     what was ordered, flags must agree with the dates and quantities they summarise
  2. the declared scenario - service levels must stay inside the bounds documented in
     docs/20, so a later change to the supplier master fails loudly instead of quietly
     turning an unreliable import vendor into a perfect one
"""
import os

import pandas as pd
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
FACT = os.path.join(PROCESSED, "fact_purchase_order_sim.parquet")
DIM_SUPPLIER = os.path.join(PROCESSED, "dim_supplier_sim.csv")
DIM_SOURCING = os.path.join(PROCESSED, "dim_family_sourcing_sim.csv")

pytestmark = pytest.mark.skipif(
    not os.path.exists(FACT),
    reason="Procurement layer not generated - run etl/phase7_procurement.py first",
)

# P-07: the whole table is simulated; only these two columns are real join keys.
REAL_JOIN_KEYS = {"store_nbr", "family"}
EXPECTED_COLUMNS = {
    "po_id", "order_date", "requested_delivery_date", "receipt_date", "store_nbr", "family",
    "supplier_id", "planned_lead_time_days", "actual_lead_time_days", "ordered_qty",
    "received_qty", "standard_cost", "po_unit_price", "po_value", "received_value",
    "ppv_per_unit", "ppv_total", "on_time_flag", "in_full_flag",
}

# Declared scenario bounds from docs/20_Procurement_Simulation.md §5.
SCENARIO_OTD_BOUNDS = (0.80, 0.92)
SCENARIO_IN_FULL_BOUNDS = (0.90, 0.97)


@pytest.fixture(scope="module")
def po():
    return pd.read_parquet(FACT)


def test_schema_is_pinned(po):
    assert set(po.columns) == EXPECTED_COLUMNS
    assert REAL_JOIN_KEYS <= set(po.columns)


def test_a_receipt_never_precedes_its_order(po):
    assert (po["receipt_date"] >= po["order_date"]).all()


def test_actual_lead_time_matches_the_dates(po):
    delta = (po["receipt_date"] - po["order_date"]).dt.days
    assert (delta == po["actual_lead_time_days"]).all()


def test_nothing_is_delivered_beyond_what_was_ordered(po):
    assert (po["received_qty"] <= po["ordered_qty"] + 1e-6).all()
    assert (po["ordered_qty"] > 0).all()


def test_flags_agree_with_the_underlying_facts(po):
    assert (po["on_time_flag"] == (po["receipt_date"] <= po["requested_delivery_date"])).all()
    assert (po["in_full_flag"] == (po["received_qty"] >= po["ordered_qty"] - 1e-6)).all()


def test_po_value_and_price_variance_are_consistent(po):
    sample = po.sample(50_000, random_state=0)
    assert ((sample["ordered_qty"] * sample["po_unit_price"] - sample["po_value"]).abs()
            < 1.0).all()
    assert ((sample["po_unit_price"] - sample["standard_cost"] - sample["ppv_per_unit"]).abs()
            < 0.01).all()


def test_every_family_is_dual_sourced_within_one_group(po):
    sourcing = pd.read_csv(DIM_SOURCING)
    dim = pd.read_csv(DIM_SUPPLIER).set_index("supplier_id")
    assert (sourcing["primary_supplier_id"] != sourcing["secondary_supplier_id"]).all()
    for row in sourcing.itertuples():
        assert dim.loc[row.primary_supplier_id, "sourcing_group"] == row.sourcing_group
        assert dim.loc[row.secondary_supplier_id, "sourcing_group"] == row.sourcing_group
    assert set(po["family"].unique()) <= set(sourcing["family"])


def test_service_levels_match_the_declared_scenario_bounds(po):
    otd, in_full = po["on_time_flag"].mean(), po["in_full_flag"].mean()
    assert SCENARIO_OTD_BOUNDS[0] <= otd <= SCENARIO_OTD_BOUNDS[1], f"OTD {otd:.1%}"
    assert SCENARIO_IN_FULL_BOUNDS[0] <= in_full <= SCENARIO_IN_FULL_BOUNDS[1], f"{in_full:.1%}"


def test_supplier_scenario_contains_price_service_tradeoffs():
    """The scenario must contain a real cost-versus-service tension - otherwise the
    procurement analysis in B6 has nothing to find.

    This checks the DESIGN CONTRACT only. It deliberately does not assert that cheap
    suppliers rank worst, because that is the kind of statement the analysis is supposed
    to discover from the data, not something the test should impose on it.
    """
    dim = pd.read_csv(DIM_SUPPLIER)

    # 1. prices are differentiated, not a single flat level
    assert dim["price_factor"].nunique() >= 3

    # 2. service levels are differentiated too
    assert dim["late_rate"].nunique() >= 3
    assert dim["in_full_rate"].nunique() >= 3

    # 3. every parameter stays inside the documented scenario bounds (docs/20 §4)
    assert dim["price_factor"].between(0.90, 1.10).all()
    assert dim["late_rate"].between(0.02, 0.40).all()
    assert dim["in_full_rate"].between(0.80, 0.99).all()
    assert dim["planned_lead_time_days"].between(1, 30).all()

    # 4. at least one genuine trade-off pair exists: someone cheaper but less reliable
    #    than someone else. Existence, not ranking.
    tradeoff = any(
        (a.price_factor < b.price_factor) and (a.late_rate > b.late_rate)
        for a in dim.itertuples() for b in dim.itertuples()
    )
    assert tradeoff, "no cheaper-but-less-reliable supplier pair in the scenario"
