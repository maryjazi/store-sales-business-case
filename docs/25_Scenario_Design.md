# 25 — Commercial Scenario Design (B7)

**Version:** 1.0  
**Last updated:** September 2026  
**Implemented by:** `etl/phase12_scenario.py`  
**Outputs:** `kpi_commercial_scenarios_sim.csv`, `kpi_scenario_summary_sim.csv`, `reports/commercial_scenarios_sim.md`

---

## 1. A decision layer, not a new simulation

This phase builds no new universe. It connects what the earlier phases produced — pricing
(B2), break-even (B3), inventory (B4), procurement (B6) and promotion (B5) — to a small set
of policy levers, and scores every scenario on one common KPI set:

`Revenue · Gross margin · Markdown · Procurement spend · Fulfilment · Inventory · OOS`

## 2. The anchor

Scenario **S0 must reproduce the committed phase-9 KPIs exactly**, and
`audit.assert_scenario_baseline_matches` checks it against the persisted files on every run.
If the baseline drifts, the layer has quietly started modelling a different business and every
comparison against it becomes meaningless — so the phase fails rather than reports.

## 3. The levers

| Scenario | Lever | Families touched |
|---|---|---|
| `S0_baseline` | current policy | 0 |
| `S1_margin_protection` | halve the discount on families with a below-median margin rate | 16 |
| `S2_availability_first` | re-source the most OOS-prone quartile to the more reliable supplier | 7 |
| `S3_growth_promotion` | deepen the discount by 5 points where estimated uplift cleared break-even | 8 |

- **S1 Margin Protection** — halve the discount on families whose margin rate is below the
  chain median. These are exactly the families where docs/23 showed a discount can barely pay
  for itself.
- **S2 Availability First** — re-source the most out-of-stock-prone quartile to the more
  reliable supplier in their own sourcing group: higher purchase price, better fill rate.
- **S3 Growth / Promotion** — deepen the discount by 5 points, but only where the estimated
  observational uplift already exceeded the break-even requirement (docs/24 §5). That gate is
  the break-even guard.

## 4. Response functions and mappings

| Quantity | How it moves | Status |
|---|---|---|
| Volume vs price | `Q′/Q = (1 + x)^e` with `e = −1.5` | **stated assumption** (docs/23 §3) |
| Fulfilled units | demand × (1 − shortfall rate) | carried from B4 |
| Shortfall (S2) | reduced by the relative gap between the current and the reliable supplier's fill rate | mapping |
| Procurement spend | ordered quantity scaled with demand, at the supplier's purchase price | mapping |
| Average inventory | scales with demand at constant weeks of supply | mapping |
| Revenue | **fulfilled** units × net price — the canonical basis since B2 | rule |

Two rules are worth stating explicitly.

**The elasticity is an assumption, not an estimate.** docs/23 explains why this project does
not estimate one.

**The observational uplift from B5 is used only as a qualification filter**, never as a
response function. It selects which families S3 may discount deeper; it never predicts how
they respond. It is an association under a calendar-matched baseline, and the placebo test in
docs/24 §3 is the reason that line is drawn.

The mappings are deliberately transparent rather than clever: a decision layer whose mechanics
cannot be explained in two lines is not a decision aid.

## 5. Results

| scenario              |   revenue_change_vs_baseline_pct |   gross_margin_change_vs_baseline_pct |   markdown_value_change_vs_baseline_pct |   procurement_spend_change_vs_baseline_pct |   avg_inventory_value_change_vs_baseline_pct |   demand_fulfillment_rate_pct_sim |   oos_day_rate_pct_sim |
|:----------------------|---------------------------------:|--------------------------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------------:|----------------------------------:|-----------------------:|
| S0_baseline           |                             0    |                                  0    |                                    0    |                                       0    |                                         0    |                             98.53 |                   1.65 |
| S1_margin_protection  |                            -1.92 |                                 11.15 |                                  -49.74 |                                      -5.74 |                                        -5.58 |                             98.53 |                   1.65 |
| S2_availability_first |                             0.05 |                                 -0.62 |                                    0.01 |                                       0.19 |                                         0    |                             98.54 |                   1.64 |
| S3_growth_promotion   |                             0.57 |                                 -3.51 |                                   15.99 |                                       1.77 |                                         1.69 |                             98.53 |                   1.65 |

Three things stand out.

**S1 is the trade-off in its purest form.** Revenue falls ~2% while gross margin rises ~11%,
markdown drops by half, and procurement spend and inventory fall with the volume. A revenue
report alone would call this scenario a loss — which is why the common KPI set exists.

**S2 barely moves anything.** Baseline fulfilment is already 98.5%, so there is little left to
buy with a more expensive, more reliable supplier: margin falls and availability gains almost
nothing. That is a result, not a failure — availability is not the binding constraint in this
scenario, and knowing that is worth more than a lever that looks busy.

**S3 exposes a genuine tension.** The families it touches are exactly those whose *observed*
uplift cleared their break-even requirement in B5 — and yet, under a stated elasticity of
−1.5, deepening their discount costs 3.5% of gross margin for 0.6% of revenue. The gate and
the response assumption disagree. Neither is wrong: the gate is observational and selects
families, the elasticity is an assumption about how they would respond. The honest reading is
that the case for deeper discounts rests entirely on which of the two you believe — and that
is precisely the question a pricing analyst should be forced to answer.

## 6. What this does not tell you

- **Never**: that a scenario *will* deliver these numbers. Each is a policy applied to a
  simulated commercial layer under a stated elasticity assumption.
- **Never**: that S3 is profitable because uplift cleared break-even in B5 — that gate is
  observational, and selects families rather than predicting their response.
- **Never**: that the mappings in §4 are estimated relationships. They are declared ones.

## 7. Related documents

- [22_Pricing_Profitability.md](22_Pricing_Profitability.md) · [23_Price_Sensitivity_Design.md](23_Price_Sensitivity_Design.md) · [24_Promotion_Effectiveness_Design.md](24_Promotion_Effectiveness_Design.md)
- [21_Inventory_Simulation.md](21_Inventory_Simulation.md) · [20_Procurement_Simulation.md](20_Procurement_Simulation.md)
- [15_ETL_Design.md](15_ETL_Design.md) §3a — schema contracts and shared audits
