"""The audits must actually catch what they claim to catch.

The reconciliation formulas live in etl/audit.py and nowhere else - the ETL scripts and
these tests call the same implementation. That leaves one thing for the tests to prove:
that the implementation is not vacuous. So each audit is fed a deliberately broken frame
and must raise.
"""
import os

import pandas as pd
import pytest

import audit
import schema

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
INV = os.path.join(PROCESSED, "fact_inventory_sim.parquet")
KPI = os.path.join(PROCESSED, "kpi_pricing_sim.csv")
BRIDGE = os.path.join(PROCESSED, "kpi_margin_bridge_sim.csv")

pytestmark = pytest.mark.skipif(
    not os.path.exists(INV), reason="pipeline outputs not generated yet")


@pytest.fixture(scope="module")
def inv_sample():
    df = schema.read_table("fact_inventory_sim.parquet", PROCESSED)
    return df.sort_values(["store_nbr", "family", "date"]).head(50_000).reset_index(drop=True)


def test_inventory_audit_passes_on_the_real_output(inv_sample):
    audit.assert_inventory_lineage(inv_sample)


def test_inventory_audit_catches_a_broken_balance(inv_sample):
    broken = inv_sample.copy()
    broken.loc[42, "closing_stock"] += 5
    with pytest.raises(audit.AuditError, match="closing"):
        audit.assert_inventory_lineage(broken)


def test_inventory_audit_catches_a_broken_carry_forward(inv_sample):
    broken = inv_sample.copy()
    broken.loc[100, "opening_stock"] += 3
    broken.loc[100, "available"] += 3
    broken.loc[100, "closing_stock"] += 3
    with pytest.raises(audit.AuditError):
        audit.assert_inventory_lineage(broken)


def test_inventory_audit_catches_a_hidden_shortage():
    """A shortage absorbed instead of surfacing is the failure mode the no-balancing-plug
    rule exists to prevent, so the audit is checked against rows that really have one."""
    df = schema.read_table("fact_inventory_sim.parquet", PROCESSED)
    shortage = df[df["unfulfilled_units_sim"] > 0].head(200).reset_index(drop=True)
    assert len(shortage) > 0, "the scenario contains no shortage at all"
    audit.assert_inventory_lineage(shortage, check_carry=False)   # unbroken: passes

    broken = shortage.copy()
    broken.loc[0, "unfulfilled_units_sim"] = 0.0
    with pytest.raises(audit.AuditError, match="unfulfilled"):
        audit.assert_inventory_lineage(broken, check_carry=False)


def test_revenue_audit_passes_and_catches():
    kpi = schema.read_table("kpi_pricing_sim.csv", PROCESSED)
    audit.assert_revenue_views(kpi)
    broken = kpi.copy()
    broken.loc[0, "revenue_sim"] = broken.loc[0, "demand_revenue_sim"] * 2
    with pytest.raises(audit.AuditError):
        audit.assert_revenue_views(broken)


def test_bridge_audit_passes_and_catches_a_nan_effect():
    bridge = schema.read_table("kpi_margin_bridge_sim.csv", PROCESSED)
    audit.assert_margin_bridge(bridge)
    broken = bridge.copy()
    broken.loc[0, "price_effect_sim"] = float("nan")
    with pytest.raises(audit.AuditError, match="undefined"):
        audit.assert_margin_bridge(broken)


def test_bridge_audit_catches_effects_that_do_not_add_up():
    bridge = schema.read_table("kpi_margin_bridge_sim.csv", PROCESSED)
    broken = bridge.copy()
    broken.loc[1, "volume_effect_sim"] += 1000.0
    with pytest.raises(audit.AuditError):
        audit.assert_margin_bridge(broken)


def test_audit_reports_missing_columns_rather_than_passing_silently():
    with pytest.raises(audit.AuditError, match="needs columns"):
        audit.assert_inventory_lineage(pd.DataFrame({"date": []}))
    with pytest.raises(audit.AuditError, match="needs columns"):
        audit.assert_revenue_views(pd.DataFrame({"revenue_sim": []}))
