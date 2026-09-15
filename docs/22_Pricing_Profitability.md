# 22 — Pricing & Profitability (B2)

**Version:** 1.0  
**Last updated:** September 2026  
**Implemented by:** `etl/phase9_pricing.py`  
**Outputs:** `data/processed/kpi_pricing_sim.csv`, `kpi_pricing_store_sim.csv`, `kpi_margin_bridge_sim.csv`, `reports/pricing_profitability_sim.md`

---

## 1. What this phase does

Nothing new is simulated here. This phase sits on the chain the previous phases built and
turns it into commercial KPIs:

```
observed units → fulfilled units_sim → net_price_sim → revenue_sim
                                     → unit_cost_sim → cogs_sim → gross_margin_sim
```

---

## 2. Which quantity carries the revenue

This is the decision the phase is built around.

Phase 6 priced every **observed** unit. Phase 8 then showed that the simulated supply chain
could not always deliver them. Booking revenue on observed units would therefore credit the
scenario with sales of goods that, inside that same scenario, were never on the shelf — an
inconsistency between the commercial layer and the inventory layer.

So both views are stated, and the gap is quantified:

| View | Definition | Role |
|---|---|---|
| Demand-side revenue | observed units × net price | potential; the benchmark the shortfall is measured against |
| **Fulfilled revenue** | **fulfilled units × net price** | **canonical from B2 onward** |
| Unfulfilled revenue | demand-side − fulfilled | must reconcile exactly |

**From this phase onward every commercial KPI uses the fulfilled quantity.** The demand-side
figure is never presented on its own, and never without the word *potential*.

The reconciliation lives in `etl/audit.py` (`assert_revenue_views`, `assert_margin_bridge`)
and is called both by phase 9 before it writes and by `tests/test_pricing_layer.py` against
the written files — see docs/15 §3a. Note that it only holds in float64: `observed_units` had to be
widened in phase 8, because a float32 × float32 product in pandas stays float32 and silently
loses the precision the identity depends on.

As in docs/21, the shortfall is a limitation of **this simulated supply chain** measured
against the observed sales quantity. It is not Favorita's lost sales.

---

## 3. KPI definitions

| KPI | Definition |
|---|---|
| `revenue_sim` | fulfilled units × net price |
| `list_revenue_sim` | fulfilled units × list price — what the same units would have earned at full price |
| `markdown_value_sim` | list revenue − net revenue |
| `markdown_pct_sim` | markdown value ÷ list revenue |
| `price_realisation_pct_sim` | net revenue ÷ list revenue (= 100 − markdown %) |
| `gross_margin_sim`, `gross_margin_pct_sim` | revenue − COGS, and as a share of revenue |
| `revenue_shortfall_pct_sim` | unfulfilled revenue ÷ demand-side revenue |
| `avg_list_price_sim`, `avg_net_price_sim`, `avg_unit_cost_sim` | value-weighted averages per unit |
| `price_position_vs_chain_pct_sim` | store-level: realised revenue ÷ revenue the same units would have earned at the chain's average net price per family. **Basket-adjusted**, so a store selling cheap families is not mistaken for a cheap store |

---

## 4. Margin bridge

The year-on-year change in gross margin, decomposed exactly:

```
volume effect = (Q₁ − Q₀) × (p₀ − c₀)
price  effect = (p₁ − p₀) × Q₁
cost   effect = −(c₁ − c₀) × Q₁
```

The three terms sum to `Q₁p₁ − Q₁c₁ − Q₀p₀ + Q₀c₀`, which is the margin change exactly. The
decomposition is computed **per family and summed**, so product mix is carried by the family
level itself and needs no separate residual mix term.

**Assortment changes.** A family that sold nothing in one of the two years has no price or
cost to compare. Those rows are labelled `assortment_change` and the whole change is booked to
the volume effect. Without that rule the price and cost terms would be `NaN`, and a skipna sum
would quietly drop them — which is exactly how a bridge stops adding up without anyone
noticing. A test asserts there are no undefined effects and that every row closes.

---

## 5. Scenario results

| KPI | Value (simulated) |
|---|---|
| Demand-side revenue (potential) | 2,297,126,088 USD |
| **Fulfilled revenue (canonical)** | **2,263,204,070 USD** |
| Revenue shortfall | 33,922,019 USD (1.48%) |
| Revenue at list price | 2,457,404,305 USD |
| Markdown given away | 194,200,235 USD (7.9% of list revenue) |
| COGS | 1,752,116,518 USD |
| Gross margin | 511,087,552 USD (22.6%) |
| Margin bridge rows | 119 normal, 13 assortment changes |

**Declared scenario bounds:** chain gross margin 20–28%, chain markdown 2–20%. Asserted in
`tests/test_pricing_layer.py`. They describe *this scenario*, not the retail sector and not
the dataset.

The 22.6% margin matches the calibration declared in docs/19 §5 — which is the point: the
margin structure set in the price book survives the supply constraint and the markdown
mechanics without being re-tuned along the way.

---

## 6. What this licenses — and what it does not

**Licensed:** pricing, markdown, margin and profitability analysis, and margin-bridge
storytelling, as a modeled commercial case, with every monetary figure labelled simulated
(P-06) and every revenue figure booked on fulfilled quantity.

**Not licensed:** any statement about Corporación Favorita's real prices, discounts, margins
or profitability; presenting demand-side revenue as achieved revenue; presenting the shortfall
as historical lost sales.

---

## 7. Related documents

- [19_Simulation_Design.md](19_Simulation_Design.md) — prices and costs
- [21_Inventory_Simulation.md](21_Inventory_Simulation.md) — where fulfilled quantity comes from
- [06_KPI_Definition.md](06_KPI_Definition.md)
- [18_Project_Roadmap.md](18_Project_Roadmap.md)
