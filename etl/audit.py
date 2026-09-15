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
