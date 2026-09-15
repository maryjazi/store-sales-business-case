# Promotion Effectiveness — three tiers, kept apart

| Tier | What it rests on | Files |
|---|---|---|
| **Real** | `onpromotion` and observed units, straight from the dataset | — |
| **Observational estimate** | real inputs, calendar-matched baseline. An estimate, **not causal** | `kpi_promotion_uplift_observational.csv`, `kpi_promotion_breadth_response_observational.csv` |
| **Scenario** | anything touching discount depth, price or margin — those are simulated (`docs/19`) | `kpi_promotion_economics_sim.csv` |
| *Method validity* | placebo and displacement diagnostics — not findings | `diagnostic_promotion_falsification.csv` |

## 1. Estimated observational uplift

Promoted days against the median of non-promoted days in the same calendar cell (store × family × period × weekday), holidays and store closures removed.

**Chain-level estimate: +52.3%.**

For context, the naive comparison in `reports/kpi_report.md` §3 — promoted rows against all non-promoted rows — gives **+619%**. Most of that number was never promotion: it was category and calendar composition. Removing it is the first result of this phase.

24.8% of promoted days rest on the strongest baseline level (same store, family, month and weekday); the rest fall back through the frozen hierarchy, and every day that finds no cell with enough support is excluded and counted rather than imputed.

## 2. Placebo test — why this is still not causal

The same estimator was run on **fake** promotion days: non-promoted days sampled to match the real promotion calendar per store, family, month and weekday (76% coverage), with the baselines rebuilt excluding those days.

**Placebo uplift: +10.6%.**

> The estimator produces non-zero uplift even under placebo assignment, indicating residual calendar/selection structure and limiting causal interpretation.

This is a method-validity diagnostic, **not a numerical lower bound**. Nothing here subtracts 10.6 from 52.3 and calls the remainder causal.

## 3. Promotion breadth response

`onpromotion` counts how many items of a family were promoted — **breadth**, not discount depth (depth is simulated). Uplift by breadth decile:

|   breadth_decile |   median_breadth |   uplift |
|-----------------:|-----------------:|---------:|
|                1 |              1   |       22 |
|               10 |              9.5 |       67 |

A monotone response is *consistent with* a real promotional effect. It does not establish one, for the same reason as §2.

## 4. Scenario economics and the break-even comparison

Two scenarios are compared directly rather than decomposed by hand: `GM_promotion = Q₁(P_promo − C)` against `GM_baseline = Q₀(P_list − C)`, so the incremental figure carries the discount on baseline units, the uplift units and the cost in one number. ROI is that figure over the markdown investment `Q₁(P_list − P_promo)`.

The comparison that matters puts the **required** uplift next to the **estimated** one. The required side is pure arithmetic (docs/23 §2); the estimated side is observational.

**8 of 32 families: estimated uplift exceeded the scenario break-even requirement.**

| family                     |   discount_depth_pct_sim |   break_even_uplift_pct_sim |   estimated_observational_uplift_pct |   uplift_gap_vs_break_even_pct_points |
|:---------------------------|-------------------------:|----------------------------:|-------------------------------------:|--------------------------------------:|
| SCHOOL AND OFFICE SUPPLIES |                     21.8 |                       103   |                               3972   |                                3869   |
| HOME AND KITCHEN II        |                     16   |                        87.8 |                                322.5 |                                 234.7 |
| PRODUCE                    |                     12.3 |                        89.7 |                                215.6 |                                 125.8 |
| HOME AND KITCHEN I         |                     15.3 |                        81.6 |                                145.6 |                                  63.9 |
| HOME CARE                  |                     15.7 |                       116.9 |                                180.6 |                                  63.7 |

And the families where it did not:

| family       |   discount_depth_pct_sim |   break_even_uplift_pct_sim |   estimated_observational_uplift_pct |   uplift_gap_vs_break_even_pct_points |
|:-------------|-------------------------:|----------------------------:|-------------------------------------:|--------------------------------------:|
| BABY CARE    |                     30   |                      2049.8 |                                305.6 |                               -1744.2 |
| PET SUPPLIES |                     30   |                      1773.3 |                                 37.3 |                               -1736   |
| SEAFOOD      |                     16.4 |                       163.7 |                                 12.9 |                                -150.8 |
| MEATS        |                     14.9 |                       158.3 |                                 12.2 |                                -146.1 |
| MAGAZINES    |                     17.8 |                       185.4 |                                 40.2 |                                -145.2 |

Note the wording: *observed uplift exceeded the scenario break-even requirement*. Not *the promotion was profitable* — the estimated side is not causal, and the economics side rests on simulated discount depths.

## 5. Cross-family displacement — an identification diagnostic, not a finding

Do other, non-promoted families move on a family's promotion days?

| Measure | Real promotion days | Placebo days |
|---|---|---|
| Other families vs their own baseline | +12.2% | +4.3% |

Other families also show higher sales on observed promotion days, which is inconsistent with a simple displacement interpretation and suggests that promotion days differ systematically from ordinary days. Placebo days show the same effect in weaker form, so part of it is calendar structure the estimator cannot remove. Which mechanism produces the difference is not identified here — busier trading days is one explanation consistent with the evidence, not a conclusion from it.

> Cannibalisation cannot be reliably identified from the available aggregation and observational design.

Family-level aggregation is too coarse (substitution happens between items, not between `GROCERY I` and `GROCERY II`), and promotion assignment is not random. Reporting a cannibalisation number here would be inventing one.

## 6. What may not be said from this page

- **Never**: that promotions *caused* the uplift, or that any promotion *was profitable*.
- **Never**: that the placebo figure may be subtracted from the estimate to recover a causal effect.
- **Never**: that `onpromotion` measures discount depth — it counts promoted items.
- **Never**: a cannibalisation figure.
