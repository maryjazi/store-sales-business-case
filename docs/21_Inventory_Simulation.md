# 21 — Inventory & Merchandising Simulation (B4)

**Version:** 1.0  
**Last updated:** September 2026  
**Implemented by:** `etl/phase8_inventory.py`  
**Outputs:** `data/processed/fact_inventory_sim.parquet`, `kpi_inventory_sim.csv`, `kpi_inventory_store_sim.csv`

---

## 1. What this phase does

It **derives** stock on hand from the purchase-order receipts of phase 7. No inventory number
is invented here: every unit in stock arrived through an order that phase 7 raised against the
real demand signal. That ordering is why sell-through, weeks of supply and out-of-stock come
out as *results* rather than as a second, independent invention.

The lineage is reconstructable for every `store × family × date`:

```
PO → Receipt → Opening Inventory → Observed Units
            → Fulfilled Units_sim → Unfulfilled Units_sim → Closing Inventory
```

---

## 2. Observed sales are not demand — and what follows from that

The Favorita data has no inventory column and no demand column. If it records 10 units sold on
a day, we cannot know whether demand was 10, or 15 with 5 lost to a stockout. **Observed sales
are a lower bound on demand, and this project never treats them as demand itself.**

Two consequences, both enforced by tests:

- When simulated stock cannot cover the observed quantity, the gap is a shortage **of this
  simulated supply chain against the observed sales quantity**. It is *not* Favorita's
  historical lost sales. The column is `unfulfilled_units_sim`, and
  `test_no_column_presents_a_shortage_as_lost_sales` fails on any column name containing
  "lost", "missed" or "forgone".
- Every rate derived from it is a **simulated** OOS rate. There is no such thing as an actual
  OOS rate on this dataset, and no output may print one.

---

## 3. The inventory equation

Auditable, with **no balancing plug and no hidden stock adjustment**:

```
available_t     = opening_t + receipts_t
fulfilled_t     = min(observed_units_t, available_t)
unfulfilled_t   = max(observed_units_t − available_t, 0)
closing_t       = available_t − fulfilled_t
opening_t+1     = closing_t
```

Closing stock can never go negative, because fulfilment is capped at availability — but a
shortage is never absorbed either: it surfaces as `unfulfilled_units_sim`.

The recursion is run **exactly**. The sales grid is complete and rectangular (1,782 series ×
1,684 days), so it is reshaped to a series × day matrix and stepped one day at a time across
all series at once — 1,684 exact iterations instead of a closed-form cumulative formula, whose
floating-point drift broke reconciliation at million-unit magnitudes. For the same reason the
seven lineage columns are stored as float64 on disk: **the audit has to hold in the delivered
artifact, not only in memory.**

The checks live in `etl/audit.py` (`assert_inventory_lineage`) and are called by phase 8
before it writes and by `tests/test_inventory_layer.py` against the written file — **one
implementation, two callers**, so the test cannot drift into certifying its own arithmetic.
That the audit is not vacuous is proved separately in `tests/test_pipeline_audits.py`, which
feeds it broken frames and requires it to raise. See docs/15 §3a.

---

## 4. Initialisation

Opening stock on the first date of each `store × family` series is **14 days of cover**, based
on that series' average daily units over its first 90 days. Series with no early activity
start at zero. This is a documented starting assumption, not a derived quantity — it is the
one number in the chain that does not come from a receipt.

---

## 5. Scenario results

| Check | Result |
|---|---|
| Observed units (real) | 1,073,644,864 |
| Fulfilled units (simulated) | 1,057,851,662 — **98.5% demand fulfillment rate** (store-side) |
| Unfulfilled units (simulated) | 15,793,291 — shortage vs observed quantity, **not lost sales** |
| Simulated OOS day rate | 1.6% of store × family × days |
| Zero-stock day rate (simulated) | 21.5% — mostly series with no demand that day |
| Lowest family sell-through | BOOKS 93.2%, BABY CARE 93.5% |
| Highest simulated family OOS rate | MAGAZINES 2.7%, AUTOMOTIVE 2.6% |

**Declared scenario bounds:** demand fulfillment rate 95–100%, simulated OOS day rate 0.5–10%. Asserted
in `tests/test_inventory_layer.py`. As in docs/19 and docs/20, the bounds describe *this
scenario* — not the retail sector and not the dataset.

### What building this phase revealed about phase 7

The first run exposed a flaw in the ordering policy: with a 5% safety margin and a minimum
order quantity charged every week, slow-moving families accumulated stock indefinitely —
BABY CARE reached **213 weeks of supply** at 20% sell-through. A planner does not order the
minimum quantity every week for an item that sells two units; they wait until the quantity is
worth ordering.

Phase 7 was therefore changed: the safety margin was removed and ordering is now lot-sized
against the family's planning order multiple — demand accumulates across weeks and an order is
raised only when it crosses the next multiple. Sell-through moved to 93–99% and weeks of
supply to a plausible 3–5 weeks for slow movers. This is exactly why inventory is derived here
instead of being generated in phase 7: deriving it made a bad ordering rule visible.

---

## 6. KPI definitions

| KPI | Definition |
|---|---|
| `sell_through_pct_sim` | fulfilled units ÷ (opening stock at period start + total receipts) |
| — | *Supplier-side service (OTD, in-full) is deliberately absent from this table — it belongs to phase 7* |
| `simulated_demand_fulfillment_rate_pct` | fulfilled units ÷ observed units — **store-side**. Not a supplier service level: supplier OTD and in-full stay in the procurement layer (docs/20), and the two must never be read as one number |
| `stock_turnover_pa_sim` | annualised fulfilled COGS ÷ average inventory value |
| `weeks_of_supply_sim` | average inventory units ÷ average weekly fulfilled units |
| `gmroi_pa_sim` | annualised fulfilled gross margin ÷ average inventory value |
| `simulated_oos_day_rate_pct` | share of store × family × days with a shortage |
| `zero_stock_day_rate_pct_sim` | share of store × family × days ending at zero stock |

**Average inventory is the daily total stock averaged over days**, not the mean of row-level
values — the latter divides by the row count and inflates turnover by orders of magnitude.
Turnover and GMROI are annualised over the 4.6-year window.

---

## 7. What this licenses — and what it does not

**Licensed:** merchandising analysis — sell-through, stock turnover, weeks of supply, GMROI,
shortage and availability patterns — as a modeled case, with every rate labelled simulated and
every monetary figure labelled simulated (P-06).

**Not licensed:** any statement about Corporación Favorita's actual stock, availability,
service levels or lost sales; any figure called an "actual OOS rate"; any treatment of
observed sales as true demand.

---

## 8. Output schema

`fact_inventory_sim.parquet` — grain: date × store × family, 3,000,888 rows.

| Column | Provenance |
|---|---|
| date, store_nbr, family, observed_units | **real** (observed_units = `sales`, a quantity) |
| receipts | from phase 7 receipts |
| opening_stock, available, closing_stock | derived (§3) |
| fulfilled_units_sim, unfulfilled_units_sim | derived (§3) |
| inventory_value_at_cost_sim, fulfilled_revenue_sim, fulfilled_cogs_sim, fulfilled_margin_sim | derived with phase-6 prices and costs — **float64**, because phase 9 derives the same concepts independently and the two layers must land on one value, not two that agree to seven digits (docs/15 §3a) |
| stockout_day_sim, zero_stock_day_sim | flags |

---

## 9. Related documents

- [19_Simulation_Design.md](19_Simulation_Design.md) — commercial layer (price, cost, margin)
- [20_Procurement_Simulation.md](20_Procurement_Simulation.md) — suppliers, POs, receipts
- [06_KPI_Definition.md](06_KPI_Definition.md)
- [18_Project_Roadmap.md](18_Project_Roadmap.md)
