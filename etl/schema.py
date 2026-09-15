"""
Typed schema contracts for every pipeline output (phases 6-9).

WHY THIS EXISTS
---------------
Phase 9 uncovered a bug that had nothing to do with phase 9: `observed_units` was written
as float32 although docs/21 stated it was float64, and a float32 x float32 product in pandas
stays float32 - so a revenue reconciliation silently lost the precision it depended on. The
real defect was not the dtype. It was that the documentation, the writing code and the file
on disk each held their own idea of the contract, and nothing ever compared them.

This module is the single source of truth. Every output table declares its columns and
dtypes once; `write_table` enforces the contract before anything is persisted and
`read_table` validates the persisted file on the way back in. A parametrised test walks
every table in SCHEMAS and checks the file on disk against its declaration, so a wrong dtype
fails where it is introduced instead of several phases downstream.

NOTE (technical debt, deliberately not done here): the quantity columns that carry audits
would be safer as fixed-point int64 milli-units, which would make the inventory equation
close exactly instead of within a tolerance. That migration touches phases 6-9, tests and
reports, so it is tracked as future hardening rather than smuggled into a structural
refactor. The dtypes below are exactly the ones the pipeline already produced - this
refactor changes no value in any output.
"""
import os
import shutil

import pandas as pd


class SchemaError(Exception):
    """Raised when a DataFrame or a persisted file violates its declared contract."""


SCHEMAS = {
    "fact_sales_commercial.parquet": {
        "phase": 6,
        "format": "parquet",
        "columns": {
            "date": "datetime64[ns]",
            "store_nbr": "int16",
            "family": "category",
            "units": "float32",
            "onpromotion": "int32",
            "list_price_sim": "float32",
            "discount_pct_sim": "float32",
            "net_price_sim": "float32",
            "unit_cost_sim": "float32",
            "revenue_sim": "float32",
            "cogs_sim": "float32",
            "gross_margin_sim": "float32",
        },
    },
    "dim_product_cost.csv": {
        "phase": 6,
        "format": "csv",
        "columns": {
            "family": "object",
            "base_price_sim": "float64",
            "cost_ratio_sim": "float64",
            "target_gross_margin_pct_sim": "float64",
        },
    },
    "dim_store_price_index.csv": {
        "phase": 6,
        "format": "csv",
        "columns": {
            "store_nbr": "int64",
            "type": "object",
            "store_price_index_sim": "float64",
        },
    },
    "fact_purchase_order_sim.parquet": {
        "phase": 7,
        "format": "parquet",
        "columns": {
            "po_id": "object",
            "order_date": "datetime64[ns]",
            "requested_delivery_date": "datetime64[ns]",
            "receipt_date": "datetime64[ns]",
            "store_nbr": "int16",
            "family": "category",
            "supplier_id": "category",
            "planned_lead_time_days": "int16",
            "actual_lead_time_days": "int16",
            "ordered_qty": "float32",
            "received_qty": "float32",
            "standard_cost": "float32",
            "po_unit_price": "float32",
            "po_value": "float32",
            "received_value": "float32",
            "ppv_per_unit": "float32",
            "ppv_total": "float32",
            "on_time_flag": "bool",
            "in_full_flag": "bool",
        },
    },
    "dim_supplier_sim.csv": {
        "phase": 7,
        "format": "csv",
        "columns": {
            "supplier_id": "object",
            "supplier_name": "object",
            "sourcing_group": "object",
            "planned_lead_time_days": "int64",
            "lead_time_sigma_days": "float64",
            "late_rate": "float64",
            "in_full_rate": "float64",
            "price_factor": "float64",
            "order_multiple": "int64",
            "families_primary": "int64",
        },
    },
    "dim_family_sourcing_sim.csv": {
        "phase": 7,
        "format": "csv",
        "columns": {
            "family": "object",
            "sourcing_group": "object",
            "primary_supplier_id": "object",
            "secondary_supplier_id": "object",
        },
    },
    "fact_inventory_sim.parquet": {
        "phase": 8,
        "format": "parquet",
        "columns": {
            "date": "datetime64[ns]",
            "store_nbr": "int16",
            "family": "category",
            "observed_units": "float64",
            "receipts": "float64",
            "opening_stock": "float64",
            "available": "float64",
            "fulfilled_units_sim": "float64",
            "unfulfilled_units_sim": "float64",
            "closing_stock": "float64",
            "inventory_value_at_cost_sim": "float64",
            "fulfilled_revenue_sim": "float64",
            "fulfilled_cogs_sim": "float64",
            "fulfilled_margin_sim": "float64",
            "stockout_day_sim": "bool",
            "zero_stock_day_sim": "bool",
        },
    },
    "kpi_inventory_sim.csv": {
        "phase": 8,
        "format": "csv",
        "columns": {
            "family": "object",
            "observed_units": "float64",
            "fulfilled_units": "float64",
            "unfulfilled_units": "float64",
            "receipts": "float64",
            "fulfilled_cogs": "float64",
            "fulfilled_margin": "float64",
            "avg_inventory_units": "float64",
            "avg_inventory_value": "float64",
            "opening_stock_start": "float64",
            "sell_through_pct_sim": "float64",
            "simulated_demand_fulfillment_rate_pct": "float64",
            "stock_turnover_pa_sim": "float64",
            "weeks_of_supply_sim": "float64",
            "gmroi_pa_sim": "float64",
            "simulated_oos_day_rate_pct": "float64",
            "zero_stock_day_rate_pct_sim": "float64",
        },
    },
    "kpi_inventory_store_sim.csv": {
        "phase": 8,
        "format": "csv",
        "columns": {
            "store_nbr": "int64",
            "observed_units": "float64",
            "fulfilled_units": "float64",
            "unfulfilled_units": "float64",
            "receipts": "float64",
            "fulfilled_cogs": "float64",
            "fulfilled_margin": "float64",
            "avg_inventory_units": "float64",
            "avg_inventory_value": "float64",
            "opening_stock_start": "float64",
            "sell_through_pct_sim": "float64",
            "simulated_demand_fulfillment_rate_pct": "float64",
            "stock_turnover_pa_sim": "float64",
            "weeks_of_supply_sim": "float64",
            "gmroi_pa_sim": "float64",
            "simulated_oos_day_rate_pct": "float64",
            "zero_stock_day_rate_pct_sim": "float64",
        },
    },
    "kpi_pricing_sim.csv": {
        "phase": 9,
        "format": "csv",
        "columns": {
            "family": "object",
            "observed_units": "float64",
            "fulfilled_units_sim": "float64",
            "demand_revenue_sim": "float64",
            "revenue_sim": "float64",
            "unfulfilled_revenue_sim": "float64",
            "list_revenue_sim": "float64",
            "markdown_value_sim": "float64",
            "cogs_sim": "float64",
            "gross_margin_sim": "float64",
            "avg_inventory_value_sim": "float64",
            "gross_margin_pct_sim": "float64",
            "markdown_pct_sim": "float64",
            "price_realisation_pct_sim": "float64",
            "revenue_shortfall_pct_sim": "float64",
            "avg_list_price_sim": "float64",
            "avg_net_price_sim": "float64",
            "avg_unit_cost_sim": "float64",
        },
    },
    "kpi_pricing_store_sim.csv": {
        "phase": 9,
        "format": "csv",
        "columns": {
            "store_nbr": "int64",
            "observed_units": "float64",
            "fulfilled_units_sim": "float64",
            "demand_revenue_sim": "float64",
            "revenue_sim": "float64",
            "unfulfilled_revenue_sim": "float64",
            "list_revenue_sim": "float64",
            "markdown_value_sim": "float64",
            "cogs_sim": "float64",
            "gross_margin_sim": "float64",
            "avg_inventory_value_sim": "float64",
            "gross_margin_pct_sim": "float64",
            "markdown_pct_sim": "float64",
            "price_realisation_pct_sim": "float64",
            "revenue_shortfall_pct_sim": "float64",
            "avg_list_price_sim": "float64",
            "avg_net_price_sim": "float64",
            "avg_unit_cost_sim": "float64",
            "price_position_vs_chain_pct_sim": "float64",
        },
    },
    "kpi_margin_bridge_sim.csv": {
        "phase": 9,
        "format": "csv",
        "columns": {
            "family": "object",
            "year": "int64",
            "bridge_case": "object",
            "margin_change_sim": "float64",
            "volume_effect_sim": "float64",
            "price_effect_sim": "float64",
            "cost_effect_sim": "float64",
            "bridge_residual": "float64",
        },
    },
    "kpi_break_even_elasticity_sim.csv": {
        "phase": 10,
        "format": "csv",
        "columns": {
            "family": "object",
            "price_change_pct": "float64",
            "baseline_units_sim": "float64",
            "baseline_revenue_sim": "float64",
            "baseline_margin_sim": "float64",
            "margin_rate_sim": "float64",
            "avg_net_price_sim": "float64",
            "avg_unit_cost_sim": "float64",
            "new_price_sim": "float64",
            "break_even_volume_ratio_sim": "float64",
            "break_even_volume_change_pct_sim": "float64",
            "feasibility_flag": "object",
            "below_cost_flag": "bool",
        },
    },
    "kpi_price_scenario_sim.csv": {
        "phase": 10,
        "format": "csv",
        "columns": {
            "family": "object",
            "price_change_pct": "float64",
            "elasticity_assumption": "float64",
            "baseline_units_sim": "float64",
            "baseline_revenue_sim": "float64",
            "baseline_margin_sim": "float64",
            "new_price_sim": "float64",
            "volume_ratio_sim": "float64",
            "new_units_sim": "float64",
            "new_revenue_sim": "float64",
            "new_cogs_sim": "float64",
            "new_margin_sim": "float64",
            "revenue_change_vs_baseline_pct": "float64",
            "margin_change_vs_baseline_pct": "float64",
            "below_cost_flag": "bool",
        },
    },
    # Kept deliberately OUTSIDE the KPI family: this is a methodological demonstration of why
    # a price/volume regression on simulated prices is not elasticity evidence (docs/23 §4),
    # not a result. The `diagnostic_` prefix is the signal.
    "diagnostic_price_volume_regression_sim.csv": {
        "phase": 10,
        "format": "csv",
        "columns": {
            "family": "object",
            "n_rows": "int64",
            "log_log_slope": "float64",
            "r_squared": "float64",
            "interpretation_warning": "object",
        },
    },
}

# Columns that carry an audit chain: they must never be narrowed, because the
# reconciliations in etl/audit.py depend on their precision.
LINEAGE_COLUMNS = {
    "fact_inventory_sim.parquet": [
        "observed_units", "receipts", "opening_stock", "available",
        "fulfilled_units_sim", "unfulfilled_units_sim", "closing_stock",
        # monetary columns: phase 9 recomputes these concepts independently, so both layers
        # must calculate in float64 or they land on two values for one concept
        "inventory_value_at_cost_sim", "fulfilled_revenue_sim", "fulfilled_cogs_sim",
        "fulfilled_margin_sim",
    ],
}


def table_names(phase=None):
    return [n for n, s in SCHEMAS.items() if phase is None or s["phase"] == phase]


def validate(df, name):
    """Return a list of contract violations (empty list means the table is valid)."""
    if name not in SCHEMAS:
        return ["%s is not declared in SCHEMAS" % name]
    declared = SCHEMAS[name]["columns"]
    problems = []
    if list(df.columns) != list(declared):
        missing = [c for c in declared if c not in df.columns]
        extra = [c for c in df.columns if c not in declared]
        if missing:
            problems.append("missing columns: %s" % missing)
        if extra:
            problems.append("undeclared columns: %s" % extra)
        if not missing and not extra:
            problems.append("column order differs from the contract")
    for col, dtype in declared.items():
        if col in df.columns and str(df[col].dtype) != dtype:
            problems.append("%s: declared %s, found %s" % (col, dtype, df[col].dtype))
    for col in LINEAGE_COLUMNS.get(name, []):
        if col in df.columns and df[col].dtype != "float64":
            problems.append("%s is a lineage column and must stay float64" % col)
    return problems


def enforce(df, name):
    """Cast a DataFrame to its declared contract and return it, or raise SchemaError."""
    if name not in SCHEMAS:
        raise SchemaError("%s is not declared in SCHEMAS" % name)
    declared = SCHEMAS[name]["columns"]
    missing = [c for c in declared if c not in df.columns]
    extra = [c for c in df.columns if c not in declared]
    if missing or extra:
        raise SchemaError("%s: missing %s, undeclared %s" % (name, missing, extra))
    out = df[list(declared)].copy()
    for col, dtype in declared.items():
        if str(out[col].dtype) != dtype:
            out[col] = out[col].astype(dtype)
    problems = validate(out, name)
    if problems:
        raise SchemaError("%s: %s" % (name, "; ".join(problems)))
    return out


def write_table(df, name, dest_dir, staging_dir=None):
    """Enforce the contract, then persist. Writing goes through a local staging directory
    first because the project folder can be a slow mount."""
    out = enforce(df, name)
    fmt = SCHEMAS[name]["format"]
    target = os.path.join(dest_dir, name)
    if staging_dir:
        os.makedirs(staging_dir, exist_ok=True)
        tmp = os.path.join(staging_dir, name)
        out.to_parquet(tmp, index=False) if fmt == "parquet" else out.to_csv(tmp, index=False)
        shutil.copyfile(tmp, target)
    else:
        out.to_parquet(target, index=False) if fmt == "parquet" else out.to_csv(target, index=False)
    return target


def read_table(name, src_dir, columns=None):
    """Read a persisted table and validate it against its contract before returning it."""
    if name not in SCHEMAS:
        raise SchemaError("%s is not declared in SCHEMAS" % name)
    path = os.path.join(src_dir, name)
    if not os.path.exists(path):
        raise SchemaError("%s has not been generated yet - run the phase that writes it" % name)
    if SCHEMAS[name]["format"] == "parquet":
        df = pd.read_parquet(path, columns=columns)
    else:
        df = pd.read_csv(path, dtype=SCHEMAS[name]["columns"], usecols=columns)
    if columns is None:
        problems = validate(df, name)
        if problems:
            raise SchemaError("%s on disk violates its contract: %s" % (name, "; ".join(problems)))
    else:
        declared = SCHEMAS[name]["columns"]
        bad = [c for c in df.columns if str(df[c].dtype) != declared[c]]
        if bad:
            raise SchemaError("%s: columns %s do not match the contract" % (name, bad))
    return df
