"""Guardrails for the simulated commercial layer (phase 6).

These tests protect two things:
  1. the arithmetic of the simulation (revenue = units x net price, etc.)
  2. the provenance convention - every simulated column must end in `_sim`,
     so the real/simulated boundary can never blur silently.
"""
import os

import pandas as pd
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
FACT = os.path.join(PROCESSED, "fact_sales_commercial.parquet")
DIM_PRODUCT = os.path.join(PROCESSED, "dim_product_cost.csv")

pytestmark = pytest.mark.skipif(
    not os.path.exists(FACT),
    reason="Commercial layer not generated - run etl/phase6_simulation_layer.py first",
)

REAL_COLUMNS = {"date", "store_nbr", "family", "units", "onpromotion"}

# Declared scenario boundary from docs/19_Simulation_Design.md §5.
# This is the margin structure THIS simulation commits to - not a claim about the
# retail sector and not a property of the Favorita dataset.
SCENARIO_MARGIN_BOUNDS = (0.20, 0.28)


@pytest.fixture(scope="module")
def fact():
    return pd.read_parquet(FACT)


def test_every_non_real_column_is_marked_simulated(fact):
    for col in fact.columns:
        if col not in REAL_COLUMNS:
            assert col.endswith("_sim"), f"{col} is neither a real column nor marked _sim"


def test_real_rows_are_preserved(fact):
    assert len(fact) == 3_000_888


def test_revenue_equals_units_times_net_price(fact):
    sample = fact.sample(50_000, random_state=0)
    expected = sample["units"] * sample["net_price_sim"]
    assert (sample["revenue_sim"] - expected).abs().max() < 1.0


def test_net_price_never_exceeds_list_price(fact):
    assert (fact["net_price_sim"] <= fact["list_price_sim"] + 1e-3).all()


def test_discount_only_on_promoted_rows(fact):
    assert (fact.loc[fact["onpromotion"] == 0, "discount_pct_sim"] == 0).all()
    promo = fact.loc[fact["onpromotion"] > 0, "discount_pct_sim"]
    assert promo.min() >= 0.05 - 1e-6
    assert promo.max() <= 0.30 + 1e-6


def test_unit_cost_is_positive(fact):
    assert (fact["unit_cost_sim"] > 0).all()


def test_chain_gross_margin_matches_the_declared_scenario_bounds(fact):
    revenue = fact["revenue_sim"].sum()
    margin = (revenue - fact["cogs_sim"].sum()) / revenue
    low, high = SCENARIO_MARGIN_BOUNDS
    assert low <= margin <= high, (
        f"simulated chain gross margin {margin:.1%} left the declared scenario bounds "
        f"{low:.0%}-{high:.0%} (docs/19 §5)"
    )


def test_price_book_covers_every_family(fact):
    dim = pd.read_csv(DIM_PRODUCT)
    assert set(fact["family"].unique()) <= set(dim["family"])
    assert (dim["cost_ratio_sim"].between(0.3, 0.95)).all()
