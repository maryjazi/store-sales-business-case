# 20 — Procurement Simulation (B6)

**Version:** 1.0  
**Last updated:** September 2026  
**Implemented by:** `etl/phase7_procurement.py`  
**Outputs:** `data/processed/fact_purchase_order_sim.parquet`, `dim_supplier_sim.csv`, `dim_family_sourcing_sim.csv`

---

## 1. Why this layer exists

Spend, purchase price variance, lead time and supplier performance all need a supply side:
a supplier master, purchase orders and receipts. The Favorita data has none of these — it
records what was sold, never what was bought. This phase creates that supply side under the
same rules as the commercial layer ([19_Simulation_Design.md](19_Simulation_Design.md)).

**It deliberately stops before inventory.** Stock on hand is derived in phase 8 from the
receipt flow produced here (`opening stock + receipts − sales`). Generating inventory here
instead would make sell-through, weeks of supply and out-of-stock *assumptions*; deriving it
from procurement makes them *results*, which is the whole point of ordering the phases this
way.

---

## 2. Provenance

| Rule | Meaning |
|---|---|
| P-07 | A table whose **name** ends in `_sim` is simulated in its entirety. Inside `fact_purchase_order_sim`, only `store_nbr` and `family` are real join keys carried over from the sales history |
| — | The **demand signal** behind the order quantities is real (`units`). The ordering policy, forecast error, suppliers, lead times, fill rates and prices are not |
| — | The schema is pinned by `tests/test_procurement_layer.py`, so a new column cannot enter undeclared |

---

## 3. The rules

| # | Rule | Detail |
|---|---|---|
| R1 | Supplier master | 14 suppliers in 6 sourcing groups; every family has a **primary and a secondary** supplier inside its group, so the same family can be compared across suppliers — which is what makes purchase price variance meaningful |
| R2 | Ordering policy | weekly replenishment against `next-week demand × (1 + forecast error)`, **no safety margin**, lot-sized against the family's planning order multiple: demand accumulates across weeks and an order is raised only when it crosses the next multiple. Orders split 70/30 between primary and secondary supplier |
| R3 | Forecast error | `N(0, 15%)` — the planner does not know next week exactly. **This error, not a random stock number, is what produces overstock and stockouts in phase 8** |
| R4 | Order timing | `order_date = start of demand week − the supplier's planned lead time`, so a reliable supplier lands the goods just as the week opens |
| R5 | Lead time | most deliveries hit the planned lead time; a supplier-specific share runs late by `1 + Poisson(σ)` days, a few arrive a day early. `on_time = receipt ≤ requested delivery` |
| R6 | Fill rate | supplier-specific (85–97% of lines in full); short deliveries arrive 5–30% short |
| R7 | Purchase price | `standard cost × supplier price factor × (1 ± 2%)`; `PPV = (purchase price − standard cost) × received qty` |

A week whose forecast comes out at zero, or whose accumulated demand has not yet reached the
next order multiple, simply produces no purchase order — a zero-quantity PO line is not a
document a planner would raise.

**Why R2 has no safety margin.** The first version ordered `demand × 1.05` and charged the
minimum order quantity every week. Phase 8 then derived the consequence: slow-moving families
accumulated stock indefinitely — BABY CARE reached 213 weeks of supply at 20% sell-through.
Lot sizing without a safety margin replaced it. See [21_Inventory_Simulation.md](21_Inventory_Simulation.md) §5.

---

## 4. Supplier master

The table encodes the classic sourcing trade-off **on purpose**: the cheap import vendors are
the unreliable ones, the dependable local suppliers charge a premium. Without that tension,
supplier analysis has nothing to find.

A test guards the **design contract** — that prices and service levels are differentiated,
that every parameter stays inside the bounds below, and that at least one cheaper-but-less-
reliable pair exists. It deliberately does **not** assert that cheap suppliers rank worst:
that is a statement the analysis should discover from the data, not one the test imposes on
it. Scenario parameter bounds: price factor 0.90–1.10, late rate 2–40%, in-full 80–99%,
planned lead time 1–30 days.

| ID | Supplier | Group | Planned LT | OTD | In full | Price factor | Spend |
|---|---|---|---|---|---|---|---|
| S01 | Local Fresh Produce Co-op A | FRESH | 2 d | 94% | 97% | 1.000 | 166.1 M |
| S02 | Local Fresh Produce Co-op B | FRESH | 3 d | 90% | 94% | 0.975 | 298.0 M |
| S03 | Regional Meat & Dairy Hub | FRESH | 4 d | 88% | 95% | 1.020 | 292.1 M |
| S04 | National Packaged Goods Ltd | PACKAGED | 6 d | 92% | 96% | 0.990 | 269.4 M |
| S05 | Regional Beverage Distributor | PACKAGED | 5 d | 86% | 93% | 1.015 | 128.8 M |
| S06 | Frozen & Chilled Logistics | PACKAGED | 7 d | 89% | 95% | 1.005 | 337.2 M |
| S07 | Household Care Wholesaler | HOUSEHOLD | 8 d | 91% | 96% | 0.985 | 195.6 M |
| S08 | Personal Care Distributor | HOUSEHOLD | 9 d | 84% | 92% | 1.030 | 116.9 M |
| S09 | Import Hardline Vendor | HARDLINE | 16 d | 72% | 88% | 0.960 | 31.2 M |
| S10 | Regional Hardware Supplier | HARDLINE | 9 d | 90% | 95% | 1.045 | 24.9 M |
| S11 | Overseas Apparel Manufacturer | APPAREL | 21 d | 68% | 85% | 0.930 | 5.7 M |
| S12 | Regional Apparel Agent | APPAREL | 11 d | 87% | 94% | 1.060 | 6.1 M |
| S13 | Publishing & Stationery Dist. | MEDIA | 7 d | 92% | 96% | 1.000 | 0.8 M |
| S14 | Import Stationery Vendor | MEDIA | 14 d | 76% | 89% | 0.950 | 1.1 M |

Supplier names are invented labels for fictional sourcing partners; they describe a role, not
a real company.

---

## 5. Scenario results

| Check | Result (all simulated) |
|---|---|
| PO lines | 294,535 across 135,541 purchase orders |
| Total spend | 1.77B USD |
| Purchase price variance | −0.91M USD (−0.05% of spend) |
| On-time delivery | 86.5% |
| In-full delivery | 93.7% |
| Average lead time | 8.1 days (planned 7.6) |
| Best / worst supplier OTD | 94% (local produce) / 68% (overseas apparel) |

**Declared scenario bounds:** chain OTD 80–92%, in-full 90–97%. Asserted in
`tests/test_procurement_layer.py` as `SCENARIO_OTD_BOUNDS` and `SCENARIO_IN_FULL_BOUNDS`.
As in docs/19 §5, these bounds describe *this scenario* — they are not a claim about the
retail sector and not a property of the dataset.

Note that chain-level PPV nets out close to zero by construction, because the price factors
sit on both sides of 1.0. The finding is not the chain total; it is the **spread between
suppliers**, and the cost-versus-service trade-off that spread pays for.

---

## 6. What this licenses — and what it does not

**Licensed:** spend analysis, purchase price variance, lead-time and service-level analysis,
supplier scorecards and sourcing trade-off discussion, presented as a modeled procurement
case on a real demand history, with every monetary figure labelled simulated (P-06).

**Not licensed:** any statement about Corporación Favorita's actual suppliers, purchase
prices, contracts or service levels. The suppliers here do not exist.

---

## 7. Output schema

`fact_purchase_order_sim.parquet` — grain: PO line (`po_id` × `store_nbr` × `family`).

| Column | Description |
|---|---|
| po_id | one PO per store × supplier × order date; several family lines share it |
| order_date, requested_delivery_date, receipt_date | R4, R5 |
| store_nbr, family | **real join keys** |
| supplier_id | R1 |
| planned_lead_time_days, actual_lead_time_days | R5 |
| ordered_qty, received_qty | R2, R6 |
| standard_cost, po_unit_price | phase 6 cost vs negotiated price (R7) |
| po_value, received_value | ordered / received × price |
| ppv_per_unit, ppv_total | R7 |
| on_time_flag, in_full_flag | service-level flags |

---

## 8. Related documents

- [19_Simulation_Design.md](19_Simulation_Design.md) — the commercial layer this builds on
- [16_Data_Model.md](16_Data_Model.md)
- [18_Project_Roadmap.md](18_Project_Roadmap.md) — Track 2 step status
