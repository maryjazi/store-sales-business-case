"""
Phase 6 - Commercial Simulation Layer (B1)

The Favorita dataset contains QUANTITIES only: `sales` is a unit count (15.4% of its
values are fractional, i.e. weighed goods) and there is no price or cost column
anywhere in the competition data. Every commercial KPI the Track-2 analyses need -
revenue, margin, markdown, price variance, stock turnover, GMROI, purchase price
variance - is therefore impossible on the raw data alone.

This phase adds a *simulated* commercial layer on top of the real sales history so
those KPIs become computable, WITHOUT touching or overwriting the real tables.

Provenance rules (kept for the whole of Track 2):
  * real columns   : date, store_nbr, family, units (= `sales`), onpromotion
                     (`onpromotion` = promotion occurrence/exposure only, not discount depth)
  * simulated cols : every column ending in `_sim`
  * the real fact table `fact_sales_actual` is never modified
  * all simulation is rule-based and deterministic (fixed seed) - no free randomness,
    so the same input always produces the same commercial layer

Simulation rules (see docs/19_Simulation_Design.md for the rationale):
  1. base price per family      - fixed price band per product family (USD; Ecuador is
                                  a USD-denominated economy, so no FX layer is needed)
  2. inflation drift            - +2.0% per year, applied per month, from 2013-01
  3. store price index          - urban/large store types price slightly above small
                                  rural ones (+-5%), so price variance ACROSS stores exists
  4. promotion discount         - promotion OCCURRENCE/EXPOSURE is real (`onpromotion`);
                                  the discount DEPTH is simulated: 5% at the lowest
                                  exposure, up to 30% at the highest. `onpromotion` says
                                  a promotion ran, never how deep the price cut was
  5. unit cost                  - family-specific cost ratio of the base price, carried
                                  centrally (NOT store-indexed), so store margin differs
  6. derived                    - revenue, cogs, gross margin, markdown %

Outputs (data/processed/):
  fact_sales_commercial.parquet  - grain: date x store x family (3,000,888 rows)
  dim_product_cost.csv           - one row per family: base price, cost ratio, target margin
  dim_store_price_index.csv      - one row per store: price index
"""
import os

import numpy as np
import pandas as pd

import schema

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
LOCAL = "/tmp/commercial_layer"
os.makedirs(LOCAL, exist_ok=True)

SEED = 42
ANNUAL_INFLATION = 0.02
MIN_DISCOUNT = 0.05
MAX_DISCOUNT = 0.30

# ---------------------------------------------------------------- price book --
# base_price_sim: plausible average selling price per unit, in USD.
# cost_ratio_sim: cost of goods as a share of the base price.
# These are ASSUMPTIONS chosen to be plausible for a grocery-format retailer
# (staples: thin margin / high cost ratio; apparel & beauty: wider margin).
# They are NOT taken from a published benchmark - see docs/19.
PRICE_BOOK = {
    "AUTOMOTIVE":                 (12.50, 0.70),
    "BABY CARE":                  ( 8.90, 0.68),
    "BEAUTY":                     ( 6.40, 0.55),
    "BEVERAGES":                  ( 1.20, 0.68),
    "BOOKS":                      ( 9.50, 0.65),
    "BREAD/BAKERY":               ( 2.10, 0.69),
    "CELEBRATION":                ( 4.80, 0.60),
    "CLEANING":                   ( 2.60, 0.70),
    "DAIRY":                      ( 1.80, 0.72),
    "DELI":                       ( 6.20, 0.71),
    "EGGS":                       ( 2.40, 0.75),
    "FROZEN FOODS":               ( 4.30, 0.70),
    "GROCERY I":                  ( 1.60, 0.73),
    "GROCERY II":                 ( 3.10, 0.71),
    "HARDWARE":                   ( 7.80, 0.68),
    "HOME AND KITCHEN I":         ( 9.20, 0.66),
    "HOME AND KITCHEN II":        (11.40, 0.66),
    "HOME APPLIANCES":            (48.00, 0.74),
    "HOME CARE":                  ( 3.40, 0.71),
    "LADIESWEAR":                 (14.60, 0.48),
    "LAWN AND GARDEN":            ( 8.70, 0.67),
    "LINGERIE":                   ( 9.80, 0.45),
    "LIQUOR,WINE,BEER":           ( 7.40, 0.70),
    "MAGAZINES":                  ( 3.20, 0.72),
    "MEATS":                      ( 5.60, 0.76),
    "PERSONAL CARE":              ( 4.10, 0.62),
    "PET SUPPLIES":               ( 6.80, 0.69),
    "PLAYERS AND ELECTRONICS":    (32.00, 0.75),
    "POULTRY":                    ( 4.20, 0.77),
    "PREPARED FOODS":             ( 5.10, 0.70),
    "PRODUCE":                    ( 1.40, 0.74),
    "SCHOOL AND OFFICE SUPPLIES": ( 2.90, 0.58),
    "SEAFOOD":                    ( 8.60, 0.74),
}

# store type -> price index (urban A stores price above small C/E stores)
TYPE_INDEX = {"A": 1.03, "B": 1.01, "C": 0.99, "D": 0.975, "E": 0.96}


def build_store_index(df):
    """One deterministic price index per store: type effect + small fixed jitter."""
    cols = ["store_nbr"] + (["type"] if "type" in df.columns else [])
    stores = df[cols].drop_duplicates().sort_values("store_nbr").reset_index(drop=True)
    if "type" in stores.columns:
        base = stores["type"].astype(str).map(TYPE_INDEX).astype("float64").fillna(1.0)
    else:
        base = 1.0
    rng = np.random.default_rng(SEED)
    jitter = rng.uniform(-0.01, 0.01, len(stores))
    stores["store_price_index_sim"] = np.round(np.asarray(base) * (1 + jitter), 4)
    return stores


def main():
    src = os.path.join(PROCESSED, "cleaned_train.parquet")
    cols = ["date", "store_nbr", "family", "sales", "onpromotion"]
    head = pd.read_parquet(src).head(0)
    if "type" in head.columns:
        cols.append("type")
    df = pd.read_parquet(src, columns=cols)
    print("loaded:", df.shape)

    missing = sorted(set(df["family"].unique()) - set(PRICE_BOOK))
    if missing:
        raise SystemExit("families missing from PRICE_BOOK: %s" % missing)

    # ---- dimensions ----
    dim_product = pd.DataFrame(
        [(f, p, c, round(1 - c, 4)) for f, (p, c) in sorted(PRICE_BOOK.items())],
        columns=["family", "base_price_sim", "cost_ratio_sim", "target_gross_margin_pct_sim"],
    )
    dim_store = build_store_index(df)

    # ---- 2. inflation drift (constant within a calendar month) ----
    months = (df["date"].dt.year - 2013) * 12 + (df["date"].dt.month - 1)
    inflation = (1 + ANNUAL_INFLATION) ** (months / 12.0)

    base_price = df["family"].map({f: p for f, (p, _) in PRICE_BOOK.items()}).astype("float64")
    cost_ratio = df["family"].map({f: c for f, (_, c) in PRICE_BOOK.items()}).astype("float64")
    store_idx = df["store_nbr"].map(
        dict(zip(dim_store["store_nbr"], dim_store["store_price_index_sim"]))
    ).astype("float64")

    # ---- 4. discount depth (simulated), scaled by real promotion exposure ----
    promo = df["onpromotion"].astype("float64")
    ref = (
        df.loc[promo > 0]
        .groupby("family", observed=True)["onpromotion"]
        .quantile(0.95)
        .replace(0, np.nan)
    )
    ref_per_row = df["family"].map(ref).astype("float64")
    intensity = np.clip(promo / ref_per_row.where(ref_per_row > 0, 1.0), 0.0, 1.0)
    discount = np.where(
        promo > 0, MIN_DISCOUNT + (MAX_DISCOUNT - MIN_DISCOUNT) * intensity, 0.0
    )

    # ---- prices, cost, derived measures ----
    list_price = base_price * inflation * store_idx
    net_price = list_price * (1 - discount)
    unit_cost = base_price * cost_ratio * inflation          # central sourcing: no store index
    units = df["sales"].astype("float64")

    out = pd.DataFrame({
        "date": df["date"],
        "store_nbr": df["store_nbr"].astype("int16"),
        "family": df["family"].astype("category"),
        "units": units.astype("float32"),                     # REAL (= cleaned_train.sales)
        "onpromotion": df["onpromotion"].astype("int32"),      # REAL
        "list_price_sim": list_price.astype("float32"),
        "discount_pct_sim": pd.Series(discount, index=df.index).astype("float32"),
        "net_price_sim": net_price.astype("float32"),
        "unit_cost_sim": unit_cost.astype("float32"),
        "revenue_sim": (units * net_price).astype("float32"),
        "cogs_sim": (units * unit_cost).astype("float32"),
    })
    out["gross_margin_sim"] = (out["revenue_sim"] - out["cogs_sim"]).astype("float32")

    # ---- write ----
    schema.write_table(out, "fact_sales_commercial.parquet", PROCESSED, LOCAL)
    schema.write_table(dim_product, "dim_product_cost.csv", PROCESSED, LOCAL)
    schema.write_table(dim_store, "dim_store_price_index.csv", PROCESSED, LOCAL)

    # ---- validation summary ----
    rev, cogs = out["revenue_sim"].sum(), out["cogs_sim"].sum()
    print("\n--- scenario summary: units and promotion occurrence are real;")
    print("    every monetary figure below is SIMULATED (see docs/19) ---")
    print("rows                : %d" % len(out))
    print("total units (real)  : %.0f" % out["units"].sum())
    print("simulated revenue   : %.0f USD" % rev)
    print("simulated margin %%  : %.1f%% (scenario bounds 20-28%%, docs/19)"
          % (100 * (rev - cogs) / rev))
    print("promo rows          : %d (%.1f%% of rows)"
          % ((out["onpromotion"] > 0).sum(), 100 * (out["onpromotion"] > 0).mean()))
    print("avg discount (sim)  : %.1f%%"
          % (100 * out.loc[out["onpromotion"] > 0, "discount_pct_sim"].mean()))
    fam_agg = out.groupby("family", observed=True)[["revenue_sim", "cogs_sim"]].sum()
    by_fam = (100 * (fam_agg["revenue_sim"] - fam_agg["cogs_sim"]) / fam_agg["revenue_sim"]).sort_values()
    print("\nsimulated margin %% by family - lowest 3:\n%s" % by_fam.head(3).round(1))
    print("simulated margin %% by family - highest 3:\n%s" % by_fam.tail(3).round(1))
    print("\nwritten to %s" % PROCESSED)


if __name__ == "__main__":
    main()
