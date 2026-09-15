"""
Phase 11 - Promotion Effectiveness (B5)

THREE TIERS, KEPT APART BY FILE NAME
------------------------------------
  REAL                    `onpromotion` and observed units come from the dataset.
  OBSERVATIONAL ESTIMATE  promoted days compared against a calendar-matched baseline built
                          from non-promoted days. The INPUTS are real; the uplift is an
                          estimate, and it is NOT causal.
  SCENARIO                anything touching discount depth, price or margin, because those
                          come from the phase-6 simulation.

  kpi_promotion_uplift_observational.csv        -> observational estimate
  kpi_promotion_breadth_response_observational.csv
  diagnostic_promotion_falsification.csv        -> method validity, not a finding
  kpi_promotion_economics_sim.csv               -> scenario economics

WHAT `onpromotion` IS
---------------------
Verified against the raw data: 362 distinct values, up to 741, median 4 on promoted rows -
it is the COUNT of promoted items inside the family, i.e. promotion **breadth**. It says
nothing about how deep the price cut was. Discount depth in this project is simulated, so
breadth (real) and depth (simulated) are never mixed into one "intensity" measure.

BASELINE (B5-1)
---------------
Median units of NON-promoted days in the same calendar cell, with a frozen fallback
hierarchy and a minimum support of 8 observations:

  L1  store x family x year-month x day-of-week      (>= 3 observations)
  L2  store x family x quarter    x day-of-week      (>= 8)
  L3  store x family x month      x day-of-week      (>= 8)
  L4  store x family x day-of-week                   (>= 8)
  L5  store x family                                 (>= 8)
  else the day is excluded and counted, never silently imputed

Minimum support is per level: a month holds only four or five occurrences of a weekday, so
L1 can never reach eight - a single global threshold silently emptied the strongest level.

Holidays are removed from both sides, and days on which a store sold nothing at all are
dropped as closures. `baseline_level_used` is reported so a reader can see how much of the
estimate rests on the strongest baseline.

PLACEBO (B5-2)
--------------
The same estimator is run on FAKE promotion days: non-promoted days sampled (seeded) to
match the real promotion calendar per store x family x month x day-of-week, with the
baselines rebuilt excluding those days. A non-zero placebo uplift indicates residual
calendar/selection structure and limits causal interpretation. It is NOT a numerical lower
bound on the real estimate, and nothing here subtracts one from the other.
"""
import os
import shutil

import numpy as np
import pandas as pd

import audit
import schema

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
REPORTS = os.path.join(ROOT, "reports")
LOCAL = "/tmp/promotion_layer"
os.makedirs(LOCAL, exist_ok=True)

SEED = 42
# Minimum support is per level, not global: a calendar month contains only four or five
# occurrences of a given weekday, so a same-month/same-weekday cell can never reach eight
# non-promoted observations. A single global threshold of 8 silently emptied L1 - the first
# run reported 0.0% of days on the strongest baseline, which is how the mis-specification
# surfaced.
LEVELS = [
    ("L1", ["store_nbr", "family", "year_month", "dow"], 3),
    ("L2", ["store_nbr", "family", "quarter", "dow"], 8),
    ("L3", ["store_nbr", "family", "month", "dow"], 8),
    ("L4", ["store_nbr", "family", "dow"], 8),
    ("L5", ["store_nbr", "family"], 8),
]


def load():
    df = schema.read_table("fact_sales_commercial.parquet", PROCESSED,
                           columns=["date", "store_nbr", "family", "units", "onpromotion",
                                    "list_price_sim", "net_price_sim", "unit_cost_sim"])
    df["family"] = df["family"].astype(str)
    for c in ("list_price_sim", "net_price_sim", "unit_cost_sim", "units"):
        df[c] = df[c].astype("float64")

    holidays = pd.read_parquet(os.path.join(PROCESSED, "cleaned_train.parquet"),
                               columns=["date", "store_nbr", "family", "is_holiday"])
    holidays["family"] = holidays["family"].astype(str)
    df = df.merge(holidays, on=["date", "store_nbr", "family"], how="left")
    df["is_holiday"] = df["is_holiday"].fillna(False).astype(bool)

    before = len(df)
    df = df[~df["is_holiday"]]
    store_day = df.groupby(["store_nbr", "date"], observed=True)["units"].transform("sum")
    df = df[store_day > 0]
    print("rows: %d -> %d after removing holidays and store closures" % (before, len(df)))

    df["dow"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["year_month"] = df["date"].dt.year * 100 + df["date"].dt.month
    df["quarter"] = df["date"].dt.year * 10 + df["date"].dt.quarter
    df["is_promo"] = df["onpromotion"] > 0
    return df.reset_index(drop=True)


def attach_baseline(target, source):
    """Median units per calendar cell, built from `source` (non-promoted days), assigned to
    `target` through the frozen fallback hierarchy."""
    expected = pd.Series(np.nan, index=target.index, dtype="float64")
    level_used = pd.Series("none", index=target.index, dtype="object")
    for name, keys, min_support in LEVELS:
        agg = source.groupby(keys, observed=True)["units"].agg(["median", "size"])
        agg = agg[agg["size"] >= min_support]["median"].rename("cell_median")
        todo = expected.isna()
        if not todo.any():
            break
        joined = target.loc[todo, keys].merge(agg, on=keys, how="left")["cell_median"]
        joined.index = target.index[todo]
        hit = joined.notna()
        expected.loc[joined.index[hit]] = joined[hit]
        level_used.loc[joined.index[hit]] = name
    return expected, level_used


def uplift_by_family(promo_rows, expected):
    ok = expected.notna()
    frame = promo_rows.loc[ok, ["family", "units"]].copy()
    frame["expected"] = expected[ok]
    g = frame.groupby("family", observed=True).agg(observed=("units", "sum"),
                                                   expected=("expected", "sum"),
                                                   days=("units", "size"))
    g["uplift_pct"] = 100 * (g["observed"] / g["expected"] - 1)
    return g


def sample_placebo(df, seed=SEED):
    """Fake promotion days matching the real promotion calendar, drawn only from days with
    onpromotion == 0. Vectorised: the pool is shuffled once with a fixed seed, ranked inside
    each calendar cell, and the first `needed` rows of each cell are taken. Coverage is
    reported rather than quietly accepted."""
    keys = ["store_nbr", "family", "month", "dow"]
    needed = df[df["is_promo"]].groupby(keys, observed=True).size().rename("needed")
    pool = df[~df["is_promo"]].sample(frac=1.0, random_state=seed)
    pool = pool.join(needed, on=keys)
    pool = pool[pool["needed"].notna()]
    rank = pool.groupby(keys, observed=True).cumcount()
    placebo = pool[rank < pool["needed"]]

    available = pool.groupby(keys, observed=True).size().rename("available")
    cover = needed.to_frame().join(available).fillna({"available": 0})
    matched = np.minimum(cover["needed"], cover["available"]).sum()
    coverage = 100.0 * matched / cover["needed"].sum() if cover["needed"].sum() else 0.0
    return placebo.drop(columns=["needed"]), float(coverage)


def main():
    df = load()
    non_promo = df[~df["is_promo"]]
    promo = df[df["is_promo"]]
    print("promoted days: %d | non-promoted days: %d" % (len(promo), len(non_promo)))

    # ---------------- B5-1: observational uplift ----------------
    expected, level = attach_baseline(promo, non_promo)
    real_uplift = uplift_by_family(promo, expected)

    lv = pd.DataFrame({"family": promo["family"].to_numpy(), "level": level.to_numpy()})
    level_share = (pd.crosstab(lv["family"], lv["level"], normalize="index") * 100).round(2)
    for col in ("L1", "L2", "L3", "L4", "L5", "none"):
        if col not in level_share.columns:
            level_share[col] = 0.0

    breadth = promo.groupby("family", observed=True)["onpromotion"].median()
    uplift_obs = pd.DataFrame({
        "family": real_uplift.index,
        "promo_days": real_uplift["days"].to_numpy(),
        "promo_days_excluded_insufficient_support":
            (promo.groupby("family", observed=True).size() - real_uplift["days"]).to_numpy(),
        "observed_units_on_promo": real_uplift["observed"].to_numpy(),
        "expected_units_observational": real_uplift["expected"].to_numpy(),
        "estimated_observational_uplift_pct": real_uplift["uplift_pct"].to_numpy(),
        "baseline_l1_share_pct": level_share.loc[real_uplift.index, "L1"].to_numpy(),
        "baseline_l2_share_pct": level_share.loc[real_uplift.index, "L2"].to_numpy(),
        "baseline_l3_share_pct": level_share.loc[real_uplift.index, "L3"].to_numpy(),
        "baseline_l4_share_pct": level_share.loc[real_uplift.index, "L4"].to_numpy(),
        "baseline_l5_share_pct": level_share.loc[real_uplift.index, "L5"].to_numpy(),
        "median_promotion_breadth": breadth.loc[real_uplift.index].to_numpy(),
    }).round(4)

    # ---------------- B5-3: breadth response ----------------
    b = promo.loc[expected.notna(), ["family", "units", "onpromotion"]].copy()
    b["expected"] = expected[expected.notna()]
    b["breadth_decile"] = (b.groupby("family", observed=True)["onpromotion"]
                            .transform(lambda s: pd.qcut(s.rank(method="first"), 10,
                                                         labels=False, duplicates="drop") + 1))
    br = (b.groupby(["family", "breadth_decile"], observed=True)
            .agg(promo_days=("units", "size"), observed_units=("units", "sum"),
                 expected_units_observational=("expected", "sum"),
                 median_promotion_breadth=("onpromotion", "median")).reset_index())
    br["estimated_observational_uplift_pct"] = 100 * (
        br["observed_units"] / br["expected_units_observational"] - 1)
    br["breadth_decile"] = br["breadth_decile"].astype("int64")
    br = br.round(4)

    # ---------------- B5-2: placebo ----------------
    placebo, coverage = sample_placebo(df)
    baseline_pool = non_promo.drop(index=placebo.index)      # placebo days are not their own baseline
    placebo_expected, _ = attach_baseline(placebo, baseline_pool)
    placebo_uplift = uplift_by_family(placebo, placebo_expected)
    print("placebo days: %d (coverage %.1f%% of the real promotion calendar)"
          % (len(placebo), coverage))

    # ---------------- B5-5: cross-family displacement diagnostic ----------------
    others = df[~df["is_promo"]].copy()
    others_exp, _ = attach_baseline(others, non_promo)
    others = others.assign(expected=others_exp).dropna(subset=["expected"])
    by_store_day = (others.groupby(["store_nbr", "date"], observed=True)
                          .agg(obs=("units", "sum"), exp=("expected", "sum")).reset_index())

    def displacement(event_rows, expected_for_events):
        """Do OTHER, non-promoted families move on the event days of this family?"""
        ev = event_rows.loc[expected_for_events.notna(), ["store_nbr", "date", "family"]]
        joined = ev.merge(by_store_day, on=["store_nbr", "date"], how="inner")
        return joined.groupby("family", observed=True).agg(obs=("obs", "sum"),
                                                           exp=("exp", "sum"))

    # AGGREGATION CONTRACT: every headline figure in this phase is a RATIO OF SUMS,
    # sum(observed) / sum(baseline) - 1, never the mean of per-row or per-family ratios.
    # A mean of ratios lets a family with a tiny baseline dominate the headline, and it would
    # make the real and placebo figures incomparable.
    def chain_ratio(g):
        return 100 * (g["obs"].sum() / g["exp"].sum() - 1)

    disp_real_totals = displacement(promo, expected)
    disp_placebo_totals = displacement(placebo, placebo_expected)
    disp_real = (100 * (disp_real_totals["obs"] / disp_real_totals["exp"] - 1)).rename("d")
    disp_placebo = (100 * (disp_placebo_totals["obs"] / disp_placebo_totals["exp"] - 1)).rename("d")
    chain_disp_real = chain_ratio(disp_real_totals)
    chain_disp_placebo = chain_ratio(disp_placebo_totals)

    families = uplift_obs["family"]
    falsification = pd.DataFrame({
        "family": families,
        "real_estimated_uplift_pct": uplift_obs["estimated_observational_uplift_pct"].to_numpy(),
        "placebo_estimated_uplift_pct": placebo_uplift["uplift_pct"].reindex(families).to_numpy(),
        "placebo_days": placebo_uplift["days"].reindex(families).fillna(0).to_numpy(),
        # the totals behind every quoted figure, so a chain-level number can be recomputed
        # as a ratio of sums straight from this file instead of averaging the percentages
        "placebo_observed_units": placebo_uplift["observed"].reindex(families).to_numpy(),
        "placebo_expected_units_observational":
            placebo_uplift["expected"].reindex(families).to_numpy(),
        "cross_family_observed_units_real": disp_real_totals["obs"].reindex(families).to_numpy(),
        "cross_family_expected_units_real": disp_real_totals["exp"].reindex(families).to_numpy(),
        "cross_family_observed_units_placebo":
            disp_placebo_totals["obs"].reindex(families).to_numpy(),
        "cross_family_expected_units_placebo":
            disp_placebo_totals["exp"].reindex(families).to_numpy(),
        "placebo_calendar_coverage_pct": round(coverage, 2),
        "cross_family_displacement_real_pct": disp_real.reindex(families).to_numpy(),
        "cross_family_displacement_placebo_pct": disp_placebo.reindex(families).to_numpy(),
        "interpretation_warning": (
            "Placebo assignment is a method-validity diagnostic, not a lower bound: a non-zero "
            "placebo uplift indicates residual calendar/selection structure and limits causal "
            "interpretation. Do not subtract one from the other."),
    }).round(4)

    # ---------------- B5-4: scenario economics ----------------
    p = promo.loc[expected.notna()].copy()
    p["expected"] = expected[expected.notna()]
    e = (p.groupby("family", observed=True)
           .apply(lambda g: pd.Series({
               "promo_days": len(g),
               "observed_units_on_promo": g["units"].sum(),
               "baseline_units_observational": g["expected"].sum(),
               "avg_list_price_sim": np.average(g["list_price_sim"], weights=g["units"].clip(lower=1e-9)),
               "avg_promo_price_sim": np.average(g["net_price_sim"], weights=g["units"].clip(lower=1e-9)),
               "avg_unit_cost_sim": np.average(g["unit_cost_sim"], weights=g["units"].clip(lower=1e-9)),
           }), include_groups=False).reset_index())
    e["gm_promotion_scenario_sim"] = e["observed_units_on_promo"] * (
        e["avg_promo_price_sim"] - e["avg_unit_cost_sim"])
    e["gm_baseline_scenario_sim"] = e["baseline_units_observational"] * (
        e["avg_list_price_sim"] - e["avg_unit_cost_sim"])
    e["incremental_gross_margin_sim"] = e["gm_promotion_scenario_sim"] - e["gm_baseline_scenario_sim"]
    e["markdown_investment_sim"] = e["observed_units_on_promo"] * (
        e["avg_list_price_sim"] - e["avg_promo_price_sim"])
    e["promo_roi_sim"] = e["incremental_gross_margin_sim"] / e["markdown_investment_sim"]
    e["list_margin_rate_sim"] = (e["avg_list_price_sim"] - e["avg_unit_cost_sim"]) / e["avg_list_price_sim"]
    e["discount_depth_pct_sim"] = 100 * (1 - e["avg_promo_price_sim"] / e["avg_list_price_sim"])
    x = -e["discount_depth_pct_sim"] / 100
    m = e["list_margin_rate_sim"]
    e["break_even_uplift_pct_sim"] = np.where(m + x > 0, 100 * (m / (m + x) - 1), np.nan)
    e["estimated_observational_uplift_pct"] = uplift_obs.set_index("family").loc[
        e["family"], "estimated_observational_uplift_pct"].to_numpy()
    e["uplift_gap_vs_break_even_pct_points"] = (
        e["estimated_observational_uplift_pct"] - e["break_even_uplift_pct_sim"])
    e["promo_days"] = e["promo_days"].astype("int64")
    # Only the presentational percentage columns are rounded. Prices, units and the margin
    # figures stay at full precision because the audit reconstructs the two scenarios from
    # them - rounded presentation outputs must never become computational inputs (docs/15).
    # discount_depth_pct_sim is excluded: it is a computational input to the break-even
    # formula, not a presentational figure (docs/15 - rounded outputs are not inputs).
    presentational = [c for c in e.columns if "_pct" in c and c != "discount_depth_pct_sim"]
    economics = e.copy()
    economics[presentational] = economics[presentational].round(4)

    audit.assert_promotion_economics(economics)
    print("promotion economics reconcile: incremental GM = scenario GM - baseline GM "
          "(etl/audit.py)")

    schema.write_table(uplift_obs, "kpi_promotion_uplift_observational.csv", PROCESSED, LOCAL)
    schema.write_table(br, "kpi_promotion_breadth_response_observational.csv", PROCESSED, LOCAL)
    schema.write_table(falsification, "diagnostic_promotion_falsification.csv", PROCESSED, LOCAL)
    schema.write_table(economics, "kpi_promotion_economics_sim.csv", PROCESSED, LOCAL)

    # ---------------- report ----------------
    chain_real = 100 * (real_uplift["observed"].sum() / real_uplift["expected"].sum() - 1)
    chain_placebo = 100 * (placebo_uplift["observed"].sum() / placebo_uplift["expected"].sum() - 1)
    above = economics[economics["uplift_gap_vs_break_even_pct_points"] > 0]
    below = economics[economics["uplift_gap_vs_break_even_pct_points"] <= 0]
    gap_cols = ["family", "discount_depth_pct_sim", "break_even_uplift_pct_sim",
                "estimated_observational_uplift_pct", "uplift_gap_vs_break_even_pct_points"]
    deciles = br[br["breadth_decile"].isin([1, 10])].groupby("breadth_decile").agg(
        median_breadth=("median_promotion_breadth", "median"),
        uplift=("estimated_observational_uplift_pct", "median")).round(1)

    lines = [
        "# Promotion Effectiveness — three tiers, kept apart",
        "",
        "| Tier | What it rests on | Files |",
        "|---|---|---|",
        "| **Real** | `onpromotion` and observed units, straight from the dataset | — |",
        "| **Observational estimate** | real inputs, calendar-matched baseline. An estimate, "
        "**not causal** | `kpi_promotion_uplift_observational.csv`, `kpi_promotion_breadth_response_observational.csv` |",
        "| **Scenario** | anything touching discount depth, price or margin — those are simulated "
        "(`docs/19`) | `kpi_promotion_economics_sim.csv` |",
        "| *Method validity* | placebo and displacement diagnostics — not findings | `diagnostic_promotion_falsification.csv` |",
        "",
        "## 1. Estimated observational uplift",
        "",
        "Promoted days against the median of non-promoted days in the same calendar cell "
        "(store × family × period × weekday), holidays and store closures removed.",
        "",
        "**Chain-level estimate: %+.1f%%.**" % chain_real,
        "",
        "For context, the naive comparison in `reports/kpi_report.md` §3 — promoted rows against "
        "all non-promoted rows — gives **+619%**. Most of that number was never promotion: it was "
        "category and calendar composition. Removing it is the first result of this phase.",
        "",
        "%.1f%% of promoted days rest on the strongest baseline level (same store, family, month "
        "and weekday); the rest fall back through the frozen hierarchy, and every day that finds "
        "no cell with enough support is excluded and counted rather than imputed."
        % uplift_obs["baseline_l1_share_pct"].mean(),
        "",
        "## 2. Placebo test — why this is still not causal",
        "",
        "The same estimator was run on **fake** promotion days: non-promoted days sampled to match "
        "the real promotion calendar per store, family, month and weekday (%.0f%% coverage), with "
        "the baselines rebuilt excluding those days." % coverage,
        "",
        "**Placebo uplift: %+.1f%%.**" % chain_placebo,
        "",
        "> The estimator produces non-zero uplift even under placebo assignment, indicating "
        "residual calendar/selection structure and limiting causal interpretation.",
        "",
        "This is a method-validity diagnostic, **not a numerical lower bound**. Nothing here "
        "subtracts %.1f from %.1f and calls the remainder causal." % (chain_placebo, chain_real),
        "",
        "## 3. Promotion breadth response",
        "",
        "`onpromotion` counts how many items of a family were promoted — **breadth**, not discount "
        "depth (depth is simulated). Uplift by breadth decile:",
        "",
        deciles.to_markdown(),
        "",
        "A monotone response is *consistent with* a real promotional effect. It does not establish "
        "one, for the same reason as §2.",
        "",
        "## 4. Scenario economics and the break-even comparison",
        "",
        "Two scenarios are compared directly rather than decomposed by hand: "
        "`GM_promotion = Q₁(P_promo − C)` against `GM_baseline = Q₀(P_list − C)`, so the "
        "incremental figure carries the discount on baseline units, the uplift units and the cost "
        "in one number. ROI is that figure over the markdown investment `Q₁(P_list − P_promo)`.",
        "",
        "The comparison that matters puts the **required** uplift next to the **estimated** one. "
        "The required side is pure arithmetic (docs/23 §2); the estimated side is observational.",
        "",
        "**%d of %d families: estimated uplift exceeded the scenario break-even requirement.**"
        % (len(above), len(economics)),
        "",
        above.nlargest(5, "uplift_gap_vs_break_even_pct_points")[gap_cols].round(1).to_markdown(index=False),
        "",
        "And the families where it did not:",
        "",
        below.nsmallest(5, "uplift_gap_vs_break_even_pct_points")[gap_cols].round(1).to_markdown(index=False),
        "",
        "Note the wording: *observed uplift exceeded the scenario break-even requirement*. Not "
        "*the promotion was profitable* — the estimated side is not causal, and the economics side "
        "rests on simulated discount depths.",
        "",
        "## 5. Cross-family displacement — an identification diagnostic, not a finding",
        "",
        "Do other, non-promoted families move on a family's promotion days?",
        "",
        "| Measure | Real promotion days | Placebo days |",
        "|---|---|---|",
        "| Other families vs their own baseline | %+.1f%% | %+.1f%% |"
        % (chain_disp_real, chain_disp_placebo),
        "",
        "Other families also show higher sales on observed promotion days, which is inconsistent "
        "with a simple displacement interpretation and suggests that promotion days differ "
        "systematically from ordinary days. Placebo days show the same effect in weaker form, so "
        "part of it is calendar structure the estimator cannot remove. Which mechanism produces "
        "the difference is not identified here — busier trading days is one explanation "
        "consistent with the evidence, not a conclusion from it.",
        "",
        "> Cannibalisation cannot be reliably identified from the available aggregation and "
        "observational design.",
        "",
        "Family-level aggregation is too coarse (substitution happens between items, not between "
        "`GROCERY I` and `GROCERY II`), and promotion assignment is not random. Reporting a "
        "cannibalisation number here would be inventing one.",
        "",
        "## 6. What may not be said from this page",
        "",
        "- **Never**: that promotions *caused* the uplift, or that any promotion *was profitable*.",
        "- **Never**: that the placebo figure may be subtracted from the estimate to recover a "
        "causal effect.",
        "- **Never**: that `onpromotion` measures discount depth — it counts promoted items.",
        "- **Never**: a cannibalisation figure.",
        "",
    ]
    path = os.path.join(LOCAL, "promotion_effectiveness.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    shutil.copyfile(path, os.path.join(REPORTS, "promotion_effectiveness.md"))

    print("\n--- promotion summary (every figure is a ratio of sums) ---")
    print("estimated observational uplift (chain): %.1f%%"
          % (100 * (real_uplift["observed"].sum() / real_uplift["expected"].sum() - 1)))
    print("placebo uplift (chain)               : %.1f%%"
          % (100 * (placebo_uplift["observed"].sum() / placebo_uplift["expected"].sum() - 1)))
    print("cross-family displacement real/placebo: %.1f%% / %.1f%%  (ratio of sums)"
          % (chain_disp_real, chain_disp_placebo))
    print("baseline from the strongest cell (L1) : %.1f%% of promoted days"
          % uplift_obs["baseline_l1_share_pct"].mean())
    above = (economics["uplift_gap_vs_break_even_pct_points"] > 0).sum()
    print("families whose estimated uplift exceeds the scenario break-even: %d of %d"
          % (above, len(economics)))
    print("\nwritten to %s" % PROCESSED)


if __name__ == "__main__":
    main()
