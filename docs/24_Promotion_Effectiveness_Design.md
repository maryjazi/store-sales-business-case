# 24 — Promotion Effectiveness Design (B5)

**Version:** 1.0  
**Last updated:** September 2026  
**Implemented by:** `etl/phase11_promotion.py`  
**Outputs:** `kpi_promotion_uplift_observational.csv`, `kpi_promotion_breadth_response_observational.csv`, `diagnostic_promotion_falsification.csv`, `kpi_promotion_economics_sim.csv`, `reports/promotion_effectiveness.md`

---

## 1. Three tiers, kept apart by file name

| Tier | Rests on | Marked by |
|---|---|---|
| **Real** | `onpromotion` and observed units, from the dataset | — |
| **Observational estimate** | real inputs, calendar-matched baseline. An estimate, **not causal** | `_observational.csv` |
| **Scenario** | discount depth, price, margin — simulated (docs/19) | `_sim.csv` |
| **Method validity** | placebo and displacement checks, not findings | `diagnostic_` prefix |

A test asserts that no `_observational` table carries a `_sim` column, so the tiers cannot
quietly merge. "Observational" means the *inputs* are real — never that the result is ground
truth.

---

## 2. B5-1 — The estimator

Promoted days are compared with the **median of non-promoted days in the same calendar cell**.
The estimand is stated plainly: *sales of this store/family on a promotion day, against its
usual level on comparable non-promotion days*.

Frozen fallback hierarchy, with **per-level** minimum support:

| Level | Cell | Min. support |
|---|---|---|
| L1 | store × family × year-month × weekday | 3 |
| L2 | store × family × quarter × weekday | 8 |
| L3 | store × family × month × weekday | 8 |
| L4 | store × family × weekday | 8 |
| L5 | store × family | 8 |
| — | no cell qualifies → **the day is excluded and counted**, never imputed | — |

Support is per level for a reason found the hard way: a calendar month holds only four or
five occurrences of a given weekday, so an L1 cell can never reach eight non-promoted
observations. A single global threshold of 8 silently emptied the strongest level — the first
run reported **0.0%** of days on L1, which is how the mis-specification surfaced. The output
carries the share of days served by each level (24.8% on L1 now), so a reader can see how
much of the estimate rests on the strongest comparison.

Holidays are removed from **both** sides (a holiday attracts promotions and demand alike), and
days on which a store sold nothing at all are dropped as closures.

**Chain-level estimate: +52.3%.**

**Aggregation contract.** Every chain-level figure in this phase is a **ratio of sums** —
`Σ observed / Σ baseline − 1` — never the mean of per-family ratios. A mean of ratios lets a
family with a tiny baseline dominate the headline, and it would make the real and placebo
figures incomparable, which is exactly what the placebo test is for. Here the two differ by
more than a percentage point, so the distinction is not academic. Every quoted figure is
reproducible from the totals stored in the output files, and a test recomputes each one and
checks it against the report.

For context, the naive comparison in `reports/kpi_report.md` §3 gives **+619%**. Most of that
was category and calendar composition, not promotion. Removing it is the first result of this
phase — a smaller number that means something.

---

## 3. B5-2 — Placebo test

The same estimator is run on **fake** promotion days: days with `onpromotion == 0`, sampled
with a fixed seed to match the real promotion calendar per store × family × month × weekday,
with the baselines rebuilt excluding those days (otherwise a placebo day would sit in its own
baseline and the test would be rigged toward zero). Calendar coverage is **76%** and is
reported rather than quietly accepted.

**Placebo uplift: +10.6%.**

> The estimator produces non-zero uplift even under placebo assignment, indicating residual
> calendar/selection structure and limiting causal interpretation.

This is a **method-validity diagnostic, not a numerical lower bound**. It does not license
subtracting the placebo figure from the estimate and calling the remainder causal, and no
column anywhere stores such a difference — a test checks for that.

---

## 4. B5-3 — Breadth, not intensity

Verified against the raw data before anything was built: `onpromotion` has 362 distinct
values, runs up to 741 and has a median of 4 on promoted rows. It is the **count of promoted
items inside the family** — promotion *breadth*. It says nothing about how deep the price cut
was, and discount depth in this project is simulated. The two are never combined into one
"intensity" measure.

Uplift by breadth decile is reported. A monotone response is *consistent with* a real
promotional effect; it does not establish one, for the same reason as §3.

---

## 5. B5-4 — Scenario economics and break-even

Two scenarios are compared directly rather than decomposed by hand:

```
GM_promotion = Q₁ × (P_promo − C)      observed units at the promoted price
GM_baseline  = Q₀ × (P_list  − C)      baseline units at list price
incremental  = GM_promotion − GM_baseline
ROI          = incremental / markdown investment,  markdown = Q₁ × (P_list − P_promo)
```

The incremental figure therefore carries the discount on baseline units, the uplift units and
the unit cost in one number, instead of three hand-rolled terms that can drift apart.
`audit.assert_promotion_economics` reconstructs every identity, including the ROI denominator.

The comparison that matters puts the **required** uplift beside the **estimated** one. The
required side is pure arithmetic — the break-even formula of docs/23 §2 applied at each
family's simulated discount depth. The estimated side is observational.

**8 of 32 families: estimated uplift exceeded the scenario break-even requirement.**

The wording is deliberate. *Observed uplift exceeded the scenario break-even requirement* —
not *the promotion was profitable*. The estimated side is not causal, and the economics side
rests on simulated discount depths. A test forbids a column named after a profitability
verdict, and checks the report for the claim too.

---

## 6. B5-5 — Cross-family displacement: an identification diagnostic

Do other, non-promoted families move on a family's promotion days?

| Measure | Real promotion days | Placebo days |
|---|---|---|
| Other families vs their own baseline | +12.2% | +4.3% |

Other families also show higher sales on observed promotion days, which is inconsistent with
a simple displacement interpretation and suggests that promotion days differ systematically
from ordinary days. Placebo days show the same effect in weaker form, so part of it is
calendar structure the estimator cannot remove. Which mechanism produces the difference is not
identified here — busier trading days is one explanation consistent with the evidence, not a
conclusion drawn from it.

> **Cannibalisation cannot be reliably identified from the available aggregation and
> observational design.**

Family-level aggregation is too coarse — substitution happens between items, not between
`GROCERY I` and `GROCERY II` — and promotion assignment is not random. Reporting a
cannibalisation number here would be inventing one. Naming the limit is the result.

---

## 7. What may not be said

- that promotions **caused** the uplift, or that any promotion **was profitable**
- that the placebo figure may be subtracted from the estimate to recover a causal effect
- that `onpromotion` measures discount depth
- any cannibalisation figure

---

## 8. Related documents

- [19_Simulation_Design.md](19_Simulation_Design.md) — R4: promotion occurrence is real, discount depth is simulated
- [23_Price_Sensitivity_Design.md](23_Price_Sensitivity_Design.md) §2 — the break-even formula used here
- [15_ETL_Design.md](15_ETL_Design.md) §3a — schema contracts and shared audits
