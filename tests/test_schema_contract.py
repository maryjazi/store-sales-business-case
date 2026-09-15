"""Every persisted pipeline output must match its declared contract.

This is the test that would have caught the float32 `observed_units` bug at the moment it
was written, instead of two phases later through a broken reconciliation.
"""
import os

import pandas as pd
import pytest

import schema

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")

GENERATED = [n for n in schema.table_names() if os.path.exists(os.path.join(PROCESSED, n))]


def test_the_contract_covers_every_phase_6_to_9_output():
    for phase in (6, 7, 8, 9):
        assert schema.table_names(phase), f"no output declared for phase {phase}"
    assert len(schema.SCHEMAS) == 12


@pytest.mark.skipif(not GENERATED, reason="pipeline outputs not generated yet")
@pytest.mark.parametrize("name", GENERATED)
def test_persisted_file_matches_its_contract(name):
    df = schema.read_table(name, PROCESSED)      # raises SchemaError on any violation
    assert schema.validate(df, name) == []


@pytest.mark.skipif(not GENERATED, reason="pipeline outputs not generated yet")
@pytest.mark.parametrize("name", [n for n in GENERATED if n in schema.LINEAGE_COLUMNS])
def test_lineage_columns_are_float64_on_disk(name):
    df = schema.read_table(name, PROCESSED, columns=schema.LINEAGE_COLUMNS[name])
    for col in schema.LINEAGE_COLUMNS[name]:
        assert df[col].dtype == "float64", f"{name}.{col} is {df[col].dtype}"


def test_enforce_rejects_a_missing_column():
    df = pd.DataFrame({"family": ["A"], "base_price_sim": [1.0], "cost_ratio_sim": [0.5]})
    with pytest.raises(schema.SchemaError):
        schema.enforce(df, "dim_product_cost.csv")


def test_enforce_rejects_an_undeclared_column():
    df = pd.DataFrame({"family": ["A"], "base_price_sim": [1.0], "cost_ratio_sim": [0.5],
                       "target_gross_margin_pct_sim": [0.5], "surprise": [1]})
    with pytest.raises(schema.SchemaError):
        schema.enforce(df, "dim_product_cost.csv")


def test_validate_flags_a_narrowed_lineage_column():
    """The exact defect the contract exists to prevent."""
    cols = schema.SCHEMAS["fact_inventory_sim.parquet"]["columns"]
    df = pd.DataFrame({c: pd.Series([0], dtype=t) for c, t in cols.items()})
    df["observed_units"] = df["observed_units"].astype("float32")
    problems = schema.validate(df, "fact_inventory_sim.parquet")
    assert any("observed_units" in p for p in problems)


def test_unknown_table_is_rejected():
    with pytest.raises(schema.SchemaError):
        schema.read_table("not_a_table.csv", PROCESSED)
