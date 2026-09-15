"""Guardrails for the promotion layer (phase 11).

This phase is the one most likely to be over-claimed, so most of these tests are about what
the outputs may say, not only about what they compute. Three tiers must stay apart: real
inputs, an observational estimate, and scenario economics that depend on simulated prices.
"""
import os
import re

import pandas as pd
import pytest

import audit
import schema

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
REPORTS = os.path.join(ROOT, "reports")
UPLIFT = os.path.join(PROCESSED, "kpi_promotion_uplift_observational.csv")

pytestmark = pytest.mark.skipif(
    not os.path.exists(UPLIFT),
    reason="Promotion layer not generated - run etl/phase11_promotion.py first",
)


@pytest.fixture(scope="module")
def uplift():
    return schema.read_table("kpi_promotion_uplift_observational.csv", PROCESSED)


@pytest.fixture(scope="module")
def economics():
    return schema.read_table("kpi_promotion_economics_sim.csv", PROCESSED)


@pytest.fixture(scope="module")
def falsification():
    return schema.read_table("diagnostic_promotion_falsification.csv", PROCESSED)


def test_nothing_anywhere_claims_causality(uplift, economics, falsification):
    """The estimand here is an association under a calendar-matched baseline. No column may
    suggest more than that."""
    banned = ("causal", "caused", "true_effect", "incremental_effect_proven")
    for df in (uplift, economics, falsification):
        for col in df.columns:
            assert not any(word in col.lower() for word in banned), col
    assert "estimated_observational_uplift_pct" in uplift.columns


def test_the_three_tiers_are_visible_in_the_file_names():
    observational = [n for n in schema.table_names(11) if n.endswith("_observational.csv")]
    scenario = [n for n in schema.table_names(11) if n.endswith("_sim.csv")]
    diagnostic = [n for n in schema.table_names(11) if n.startswith("diagnostic_")]
    assert observational and scenario and diagnostic
    # an observational table may not carry simulated price or margin columns
    for name in observational:
        cols = schema.SCHEMAS[name]["columns"]
        assert not any(c.endswith("_sim") for c in cols), name


def test_uplift_is_the_ratio_it_claims_to_be(uplift):
    implied = 100 * (uplift["observed_units_on_promo"]
                     / uplift["expected_units_observational"] - 1)
    assert ((implied - uplift["estimated_observational_uplift_pct"]).abs() < 1e-3).all()


def test_baseline_levels_are_fully_accounted_for(uplift):
    """Whatever does not come from one of the five levels must be the days that were
    excluded for insufficient support - nothing may vanish between the two."""
    shares = uplift[[c for c in uplift.columns if c.startswith("baseline_l")]].sum(axis=1)
    total_days = uplift["promo_days"] + uplift["promo_days_excluded_insufficient_support"]
    excluded_share = 100 * uplift["promo_days_excluded_insufficient_support"] / total_days
    assert ((shares + excluded_share - 100).abs() < 0.1).all(), (
        "baseline level shares plus excluded days do not add up to 100")
    assert (uplift["baseline_l1_share_pct"] > 0).any(), (
        "no day uses the strongest baseline - the support thresholds are mis-specified")
    assert (uplift["promo_days_excluded_insufficient_support"] >= 0).all()


def test_placebo_is_reported_as_a_diagnostic_not_a_correction(falsification):
    assert (falsification["placebo_days"] > 0).all()
    assert falsification["placebo_calendar_coverage_pct"].between(0, 100).all()
    warning = falsification["interpretation_warning"].iloc[0].lower()
    assert "not a lower bound" in warning
    assert "do not subtract" in warning
    # the corrected value must not be precomputed anywhere - that is the subtraction the
    # warning forbids
    assert not any("net_of_placebo" in c or "corrected" in c for c in falsification.columns)


def test_promotion_economics_pass_the_shared_audit(economics):
    audit.assert_promotion_economics(economics)


def test_the_economics_audit_catches_a_broken_identity(economics):
    broken = economics.copy()
    broken.loc[0, "incremental_gross_margin_sim"] += 1000.0
    with pytest.raises(audit.AuditError):
        audit.assert_promotion_economics(broken)


def test_break_even_comparison_is_a_gap_not_a_verdict(economics):
    implied = (economics["estimated_observational_uplift_pct"]
               - economics["break_even_uplift_pct_sim"])
    ok = implied.notna()
    assert ((implied[ok] - economics["uplift_gap_vs_break_even_pct_points"][ok]).abs()
            < 1e-3).all()
    assert not any("profitable" in c.lower() or "verdict" in c.lower()
                   for c in economics.columns)


def test_break_even_follows_the_documented_formula(economics):
    m = economics["list_margin_rate_sim"]
    x = -economics["discount_depth_pct_sim"] / 100
    expected = 100 * (m / (m + x) - 1)
    ok = (m + x) > 0
    assert ((expected[ok] - economics["break_even_uplift_pct_sim"][ok]).abs() < 1e-3).all()
    assert economics["break_even_uplift_pct_sim"][~ok].isna().all()


def test_the_report_does_not_overclaim():
    """The written page is part of the deliverable, so it is checked like the data."""
    text = open(os.path.join(REPORTS, "promotion_effectiveness.md"), encoding="utf-8").read().lower()
    for phrase in ("proves that", "causal effect of promotion", "promotions caused",
                   "promotions were profitable"):
        assert phrase not in text, f"the report claims: {phrase}"
    # "was profitable" may appear only inside an explicit negation: the report states what it
    # deliberately does NOT claim, and that sentence must not trip its own guardrail. The
    # whole line is inspected, because the negation can sit at the start of a bullet.
    for line in text.splitlines():
        if "profitable" in line:
            assert re.search(r"\bnot\b|\bnever\b|may not be said", line), (
                "the report claims profitability: %s" % line.strip())
    assert "not causal" in text
    assert "cannot be reliably identified" in text


def test_headline_figures_are_ratios_of_sums_not_means_of_ratios(uplift, falsification):
    """Aggregation contract: every chain-level figure is sum(observed)/sum(baseline) - 1.

    A mean of per-family ratios would let a family with a tiny baseline dominate the
    headline, and it would make the real and placebo figures incomparable - which is the
    whole point of running the placebo. Each quoted number must therefore be reproducible
    from the totals in these files.
    """
    report = open(os.path.join(REPORTS, "promotion_effectiveness.md"), encoding="utf-8").read()

    chain_real = 100 * (uplift["observed_units_on_promo"].sum()
                        / uplift["expected_units_observational"].sum() - 1)
    chain_placebo = 100 * (falsification["placebo_observed_units"].sum()
                           / falsification["placebo_expected_units_observational"].sum() - 1)
    chain_disp = 100 * (falsification["cross_family_observed_units_real"].sum()
                        / falsification["cross_family_expected_units_real"].sum() - 1)

    for value in (chain_real, chain_placebo, chain_disp):
        assert f"{value:+.1f}%" in report or f"{value:.1f}%" in report, (
            f"{value:.1f}% is not the figure the report quotes")

    # the mean of ratios is a different number here - proof the distinction is not academic
    mean_of_ratios = uplift["estimated_observational_uplift_pct"].mean()
    assert abs(mean_of_ratios - chain_real) > 1.0
