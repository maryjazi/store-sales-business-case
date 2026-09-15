# 19 — Simulation Design (Commercial Layer)

**Version:** 1.1  
**Last updated:** September 2026  
**Implemented by:** `etl/phase6_simulation_layer.py`  
**Outputs:** `data/processed/fact_sales_commercial.parquet`, `dim_product_cost.csv`, `dim_store_price_index.csv`

---

## 1. Why this layer exists

The Favorita competition data contains **quantities only**. Two facts establish this:

- 15.4% of all `sales` values are fractional (e.g. `BREAD/BAKERY 180.589`, `DELI 71.09`) — a
  currency amount does not carry fractional weight units, a kilogram price does.
- The dataset ships **no price column**, and no cost, inventory, supplier or purchase-order
  table of any kind.

Every commercial KPI in the Track-2 scope — revenue, gross margin, markdown, price variance,
price elasticity, sell-through, stock turnover, GMROI, spend, purchase price variance — is
therefore *not computable* on the raw data. This is not specific to Favorita: cost and
inventory are internal ERP data that no retailer publishes, so no public retail dataset
(M5, Rossmann, Favorita) contains them.

The choice was therefore never "real data or simulated data". It was "a commercial layer
built on explicit rules, or no commercial analysis at all". This document is the price of
the first option: every assumption stated, so a reader can judge the analysis.

---

## 2. Provenance rules

These hold for the whole of Track 2 and are enforced by `tests/test_simulation_layer.py`:

| Rule | Meaning |
|---|---|
| P-01 | Real columns keep their plain name: `date`, `store_nbr`, `family`, `units`, `onpromotion` |
| P-02 | **Every simulated column ends in `_sim`** — a test fails if any column is neither real nor suffixed |
| P-03 | The real fact table `fact_sales_actual` is never modified; the commercial layer is a separate table |
| P-04 | Simulation is rule-based and deterministic (`SEED = 42`); the same input always yields the same layer |
| P-05 | No output of this project claims a real Favorita price, cost, margin or inventory figure |
| P-07 | A table whose **name** ends in `_sim` is simulated in its entirety (e.g. `fact_purchase_order_sim`); inside such a table only `store_nbr` and `family` are real join keys |
| P-06 | **Every monetary figure is labelled as simulated wherever it appears** — report, dashboard KPI title or tooltip, CV bullet. "Simulated revenue: $2.30B", never "Revenue: $2.30B" |

---

## 3. The rules

| # | Rule | Formula |
|---|---|---|
| R1 | Base price per family | fixed price band per product family, in USD (Ecuador is a USD-denominated economy, so no FX layer is needed) |
| R2 | Inflation drift | `factor = 1.02 ^ (months_since_2013-01 / 12)`, constant within a calendar month |
| R3 | Store price index | store-type effect (A 1.03 … E 0.96) plus a fixed ±1% jitter, so **price variance across stores exists** |
| R4 | Promotion discount | exposure comes from the real `onpromotion` count: `exposure = clip(onpromotion / p95(onpromotion per family), 0, 1)`, then `discount = 0.05 + 0.25 × exposure`; zero on non-promoted rows |
| R5 | Unit cost | `base_price × cost_ratio × inflation` — **not** store-indexed, because sourcing is central; this is what makes store margins differ |
| R6 | Derived | `list_price = base × inflation × store_index`, `net_price = list × (1 − discount)`, `revenue = units × net_price`, `cogs = units × unit_cost`, `gross_margin = revenue − cogs`, `markdown % = discount %` |

**R4, stated precisely.** `onpromotion` records *that* a family was under promotion at a store
on a date, and how many of its items were — that is **promotion occurrence and exposure, and
it is real**. It says nothing about how deep the price cut was. The **discount depth is
simulated**: the rule maps a high exposure to a deeper assumed discount, which is a modelling
choice, not an observation. This boundary matters in B5 (promotion effectiveness): uplift may
be built on the real occurrence, but anything that depends on discount depth — promo ROI,
margin sacrificed per promotion — is scenario output.

---

## 4. Price book

`base_price_sim` is a plausible average selling price per unit; `cost_ratio_sim` is cost of
goods as a share of that price. Staples carry a high cost ratio (thin margin), apparel and
beauty a low one.

| Family | Base price (USD) | Cost ratio | Target gross margin |
|---|---|---|---|
| AUTOMOTIVE | 12.50 | 0.70 | 30% |
| BABY CARE | 8.90 | 0.68 | 32% |
| BEAUTY | 6.40 | 0.55 | 45% |
| BEVERAGES | 1.20 | 0.68 | 32% |
| BOOKS | 9.50 | 0.65 | 35% |
| BREAD/BAKERY | 2.10 | 0.69 | 31% |
| CELEBRATION | 4.80 | 0.60 | 40% |
| CLEANING | 2.60 | 0.70 | 30% |
| DAIRY | 1.80 | 0.72 | 28% |
| DELI | 6.20 | 0.71 | 29% |
| EGGS | 2.40 | 0.75 | 25% |
| FROZEN FOODS | 4.30 | 0.70 | 30% |
| GROCERY I | 1.60 | 0.73 | 27% |
| GROCERY II | 3.10 | 0.71 | 29% |
| HARDWARE | 7.80 | 0.68 | 32% |
| HOME AND KITCHEN I | 9.20 | 0.66 | 34% |
| HOME AND KITCHEN II | 11.40 | 0.66 | 34% |
| HOME APPLIANCES | 48.00 | 0.74 | 26% |
| HOME CARE | 3.40 | 0.71 | 29% |
| LADIESWEAR | 14.60 | 0.48 | 52% |
| LAWN AND GARDEN | 8.70 | 0.67 | 33% |
| LINGERIE | 9.80 | 0.45 | 55% |
| LIQUOR,WINE,BEER | 7.40 | 0.70 | 30% |
| MAGAZINES | 3.20 | 0.72 | 28% |
| MEATS | 5.60 | 0.76 | 24% |
| PERSONAL CARE | 4.10 | 0.62 | 38% |
| PET SUPPLIES | 6.80 | 0.69 | 31% |
| PLAYERS AND ELECTRONICS | 32.00 | 0.75 | 25% |
| POULTRY | 4.20 | 0.77 | 23% |
| PREPARED FOODS | 5.10 | 0.70 | 30% |
| PRODUCE | 1.40 | 0.74 | 26% |
| SCHOOL AND OFFICE SUPPLIES | 2.90 | 0.58 | 42% |
| SEAFOOD | 8.60 | 0.74 | 26% |

---

## 5. Calibration

Cost ratios are **scenario assumptions**, calibrated to produce a commercially plausible,
internally consistent margin structure. They are **not** estimates of Corporación Favorita's
actual costs or margins, and the bounds below are not taken from a published benchmark — they
are the scenario boundary this project commits to and tests against.

The calibration target is the **realized** margin, i.e. what remains after the promotion
discounts of R4 have eaten into the list margin — not the list margin itself.

| Check | Result |
|---|---|
| Total units (real) | 1.07B units |
| **Simulated** revenue | 2.30B USD |
| **Simulated** chain gross margin | **22.6%** |
| Promoted rows (real occurrence) | 611,329 (20.4%) |
| Average **simulated** discount on promoted rows | 12.6% |
| Thinnest family margin (simulated) | GROCERY I, 18.0% |
| Widest family margin (simulated) | LINGERIE, 54.3% |

**Scenario bounds: 20–28% realized chain gross margin.** These are asserted in
`tests/test_simulation_layer.py` as `SCENARIO_MARGIN_BOUNDS`, so a later change to the price
book that drifts out of the declared scenario fails the test suite instead of passing
silently. The bounds describe *this scenario*, not the retail sector and not the dataset.

---

## 6. What this licenses — and what it does not

**Licensed:** computing and presenting pricing, margin, markdown, inventory, procurement and
promotion KPIs as a *modeled commercial case* on a real sales history, with every monetary
figure labelled as simulated (P-06).

**Not licensed:**

- Any statement about Corporación Favorita's actual prices, costs, margins or suppliers.
- Presenting price elasticity as an estimate of Favorita's historical elasticity. Because
  `net_price_sim` is generated by R4, the observed price/quantity relationship partly reflects
  the rule itself. Elasticity work is therefore labelled **scenario-based / simulated price
  elasticity analysis**.
- Promotion *uplift* claims that rest on the simulation. Uplift may be built on the real
  promotion occurrence, but a causal claim needs a matched-baseline design — a simple
  promo vs non-promo comparison is correlational (see `reports/kpi_report.md` §3).
- Any monetary KPI presented without its provenance, in any medium.

---

## 7. Output schema

`fact_sales_commercial.parquet` — grain: date × store × family, 3,000,888 rows.

| Column | Provenance | Description |
|---|---|---|
| date, store_nbr, family | real | grain keys |
| units | real | `cleaned_train.sales` — a quantity |
| onpromotion | real | promotion occurrence/exposure: items of that family on promotion, that store, that day |
| list_price_sim | simulated | R1 × R2 × R3 |
| discount_pct_sim | simulated | R4 — depth is modelled, exposure is not (also the markdown %) |
| net_price_sim | simulated | list × (1 − discount) |
| unit_cost_sim | simulated | R5 |
| revenue_sim, cogs_sim, gross_margin_sim | simulated | R6 |

---

## 8. Related documents

- [08_Data_Dictionary.md](08_Data_Dictionary.md)
- [11_Business_Rules.md](11_Business_Rules.md) — BR-R02: all raw sales figures are quantities
- [12_Assumptions_Constraints.md](12_Assumptions_Constraints.md) — A-02
- [18_Project_Roadmap.md](18_Project_Roadmap.md)
