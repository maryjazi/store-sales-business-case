# 23 — Price Sensitivity & Break-even Design (B3)

**Version:** 1.0  
**Last updated:** September 2026  
**Implemented by:** `etl/phase10_price_sensitivity.py`  
**Outputs:** `data/processed/kpi_break_even_elasticity_sim.csv`, `kpi_price_scenario_sim.csv`, `diagnostic_price_volume_regression_sim.csv`, `reports/price_sensitivity_sim.md`

---

## 1. What this phase refuses to do

It does not estimate a price elasticity, and the refusal is the design decision, not a gap.

`net_price_sim` is *generated* by the phase-6 rules: promotion depth (R4), the store price
index (R3) and inflation drift (R2). Regressing observed quantities on those prices recovers
the rules we wrote. A number comes out, it looks like an elasticity, and it is circular.

The honest alternative turns out to be stronger, because the question a pricing analyst
actually needs answered does not require a behavioural estimate at all.

---

## 2. B3-1 — Break-even analysis (no behavioural assumption)

How much volume a price change could afford to lose, or would have to gain, for gross margin
to stay flat. With current price `P`, unit cost `C`, margin rate `m = (P − C) / P` and a
relative price change `x`:

```
Q(P − C) = Q′[P(1+x) − C]        and        C = P(1 − m)
⇒  P(1+x) − C = P(m + x)
⇒  Q′/Q = m / (m + x)
```

At the chain's simulated margin of 22.6%:

| Price change | Volume needed to hold margin |
|---|---|
| +5% | may fall 18.1% |
| +10% | may fall 30.7% |
| −5% | must rise 28.4% |
| −10% | must rise 79.5% |

**This is margin arithmetic, not a forecast.** `audit.assert_break_even_roundtrip` rebuilds
the margin from the ratio and the new price and requires the baseline back, so the claim is
checked rather than trusted.

One implementation detail matters: average price and cost are recomputed from the totals
rather than read from the rounded per-unit KPI columns. The ratio has a tiny denominator when
the price cut approaches the margin, so a third-decimal rounding in the price is amplified
into a double-digit error — and the round-trip audit correctly refused the first version that
did it that way.

### The finding

Break-even depends entirely on the starting margin, so the same discount is a completely
different proposition per category. At a 10% price cut:

| Family (thinnest margins) | Margin rate | Volume needed |
|---|---|---|
| GROCERY I | 18.0% | +124.3% |
| POULTRY | 19.7% | +103.5% |
| PRODUCE | 20.0% | +99.7% |

| Family (widest margins) | Margin rate | Volume needed |
|---|---|---|
| LINGERIE | 54.3% | +22.5% |
| LADIESWEAR | 51.8% | +23.9% |
| BEAUTY | 41.9% | +31.4% |

For thin-margin staples a 10% discount needs the volume to roughly double before it pays for
itself. That is a usable pricing rule, derived without estimating anything about customers.

### Rows that cannot be restored

When the price cut is deeper than the margin (`m + x ≤ 0`), **no volume restores the margin** —
every extra unit loses money. Those rows are flagged `margin_cannot_be_restored` and carry no
ratio at all, rather than a misleading number. Rows whose new price falls below unit cost
carry `below_cost_flag`; they are kept and flagged, never silently dropped.

---

## 3. B3-2 — Elasticity sensitivity (explicit assumptions)

Three assumed elasticities — **−1.0, −1.5, −2.0** — run through the full chain: volume →
revenue → COGS → gross margin → change against baseline.

| Choice | Value |
|---|---|
| Functional form | constant elasticity, `Q′/Q = (1+x)^e` |
| Unit cost | held constant |
| Grid | 10 price steps × 3 assumptions × 33 families = 990 rows |
| Below-cost rows | flagged, kept |

These are **assumptions, stated as assumptions**. The column is named
`elasticity_assumption`, never `elasticity_estimate`.

The output carries `margin_change_vs_baseline_pct` alongside
`revenue_change_vs_baseline_pct`, because the decision a pricing analyst faces is exactly that
trade-off: a price increase can lose revenue while gaining gross margin, and a discount can do
the reverse. A grid that reported revenue alone would hide the decision.

---

## 4. B3-3 — Methodological guardrail

> The observed relationship between simulated prices and observed quantities is mechanically
> contaminated by the scenario construction and must not be interpreted as an estimate of
> customer price elasticity.

The regression is computed and kept — as a demonstration, not a result. It lives in
`diagnostic_price_volume_regression_sim.csv` (the `diagnostic_` prefix is the signal), it is
declared in the schema outside the KPI family, and a test asserts it never leaks into a KPI
output.

The fitted log-log slopes make the point better than the argument does:

| Family | Fitted slope | R² |
|---|---|---|
| MAGAZINES | +8.58 | 0.065 |
| PLAYERS AND ELECTRONICS | +8.22 | 0.076 |
| GROCERY II | +3.86 | 0.022 |
| SCHOOL AND OFFICE SUPPLIES | -8.48 | 0.216 |
| PRODUCE | -4.99 | 0.028 |
| HOME AND KITCHEN II | -3.68 | 0.102 |

A "price elasticity" of **+8.6** is not a weak result — it is a meaningless one. Promotion
weeks carry both the deep discount and the high volume, so the slope measures a shared cause:
promotion intensity. Where the store price index dominates instead, the sign flips. The
coefficients describe `phase6_simulation_layer.py`, not shoppers.

The slopes above are what this run produced; they illustrate the point rather than prove
it. The guardrail holds whatever sign the coefficients take — if upstream data or scenario
rules changed and every slope turned negative, the number would still not be a causal
elasticity. The test suite therefore pins the *methodology* (the diagnostic stays out of the
KPI outputs, carries its warning, and is never labelled an estimate) and does not require CI
to reproduce a particular coefficient.

This is why the project answers the pricing question with break-even arithmetic (§2) and
stated assumptions (§3) rather than with an estimate.

---

## 5. What this licenses — and what it does not

**Licensed:** break-even and price-sensitivity analysis per category, scenario comparison
under stated elasticity assumptions, and the revenue-versus-margin trade-off discussion.
In a CV: *Break-even- und Preissensitivitätsanalyse je Warengruppe*.

**Not licensed:** *Price Elasticity Estimation*; any presentation of the diagnostic slopes as
a finding; any claim about how Favorita's customers respond to price.

---

## 6. Related documents

- [19_Simulation_Design.md](19_Simulation_Design.md) — why prices are simulated, and R2–R4
- [22_Pricing_Profitability.md](22_Pricing_Profitability.md) — the baseline this phase starts from
- [15_ETL_Design.md](15_ETL_Design.md) §3a — schema contracts and shared audits
