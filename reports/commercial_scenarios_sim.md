# Commercial Scenarios — a decision layer, not a new simulation

Every figure is **simulated** (`docs/19`). This page changes no data: it applies policy
levers to the universe phases 6–11 already built and scores each scenario on one common
KPI set. Scenario **S0 reproduces the committed phase-9 KPIs exactly** — an audit fails
the phase if it does not, because a decision layer that drifts from its own baseline is
no longer describing the same business.

| Scenario | Lever | Families touched |
|---|---|---|
| `S0_baseline` | current policy | 0 |
| `S1_margin_protection` | halve the discount on families with a below-median margin rate | 16 |
| `S2_availability_first` | re-source the most OOS-prone quartile to the more reliable supplier | 7 |
| `S3_growth_promotion` | deepen the discount by 5 points where estimated uplift cleared break-even | 8 |

## Scored on the common KPI set

Changes against baseline, in percent:

| scenario              |   revenue_change_vs_baseline_pct |   gross_margin_change_vs_baseline_pct |   markdown_value_change_vs_baseline_pct |   procurement_spend_change_vs_baseline_pct |   avg_inventory_value_change_vs_baseline_pct |   demand_fulfillment_rate_pct_sim |   oos_day_rate_pct_sim |
|:----------------------|---------------------------------:|--------------------------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------------:|----------------------------------:|-----------------------:|
| S0_baseline           |                             0    |                                  0    |                                    0    |                                       0    |                                         0    |                             98.53 |                   1.65 |
| S1_margin_protection  |                            -1.92 |                                 11.15 |                                  -49.74 |                                      -5.74 |                                        -5.58 |                             98.53 |                   1.65 |
| S2_availability_first |                             0.05 |                                 -0.62 |                                    0.01 |                                       0.19 |                                         0    |                             98.54 |                   1.64 |
| S3_growth_promotion   |                             0.57 |                                 -3.51 |                                   15.99 |                                       1.77 |                                         1.69 |                             98.53 |                   1.65 |

## How to read this

Volume responds to price through the **stated elasticity assumption** of docs/23 §3
(-1.5, constant-elasticity form). It is an assumption, not an estimate.

The observational uplift from B5 is used **only as a qualification filter** in S3 —
which families are allowed a deeper discount — and never as a response function. It is
an association under a calendar-matched baseline, not a causal coefficient, and the
placebo test in docs/24 §3 is the reason that distinction is kept.

Inventory, procurement spend and shortfall follow proportional mappings documented in
`docs/25_Scenario_Design.md` §4. They are deliberately transparent rather than clever:
a decision layer whose mechanics cannot be explained in two lines is not a decision aid.

## What this does not tell you

- **Never**: that a scenario *will* deliver these numbers. Each one is a policy applied
  to a simulated commercial layer under a stated elasticity assumption.
- **Never**: that S3 is profitable because uplift cleared break-even in B5 — that gate
  is observational, and it selects families rather than predicting their response.
