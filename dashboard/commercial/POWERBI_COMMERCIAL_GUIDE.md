# Power BI build guide — Commercial Cockpit

The model in this folder is written by `etl/phase13_commercial_export.py` and is the same one
the Streamlit cockpit (`dashboard/commercial_app.py`) reads. Power BI Desktop opens Parquet
natively (Get Data → Parquet) and CSV through Text/CSV.

> **The one rule this guide exists to enforce.** Every measure name carries its provenance —
> `Revenue (simulated)`, never `Revenue`. The suffix comes from `dim_measure_provenance.csv`,
> which declares what each measure rests on. If you add a measure, add its row there first;
> the Streamlit cockpit raises on an undeclared measure and this guide asks the same of you.

---

## 1. Tables

| Table | File | Grain |
|---|---|---|
| `fact_commercial_monthly` | `fact_commercial_monthly.parquet` | month × store × family |
| `fact_procurement_monthly` | `fact_procurement_monthly.parquet` | month × store × family × supplier |
| `dim_family_commercial` | `dim_family_commercial.csv` | family |
| `dim_supplier_commercial` | `dim_supplier_commercial.csv` | supplier |
| `dim_measure_provenance` | `dim_measure_provenance.csv` | measure (reference, not related) |
| `dim_store` | `../data/dim_store.csv` | store |

Add a date table over `month` (Modeling → New table):

```dax
dim_month = CALENDAR(DATE(2013,1,1), DATE(2017,8,1))
```

then Mark as date table, and keep the relationship at month grain — the facts are monthly, so
a daily date table without a month key will produce blanks.

## 2. Relationships

```
dim_month[Date]              1 --- * fact_commercial_monthly[month]
dim_store[store_nbr]         1 --- * fact_commercial_monthly[store_nbr]
dim_family_commercial[family]1 --- * fact_commercial_monthly[family]
dim_month[Date]              1 --- * fact_procurement_monthly[month]
dim_family_commercial[family]1 --- * fact_procurement_monthly[family]
dim_supplier_commercial[supplier_id] 1 --- * fact_procurement_monthly[supplier_id]
```

`dim_measure_provenance` stays unrelated — it is documentation the report can display.

## 3. Measures

```dax
-- Executive
Revenue (simulated) = SUM(fact_commercial_monthly[revenue_sim])
COGS (simulated) = SUM(fact_commercial_monthly[cogs_sim])
Gross Margin (simulated) = SUM(fact_commercial_monthly[gross_margin_sim])
Gross Margin % (simulated) = DIVIDE([Gross Margin (simulated)], [Revenue (simulated)])
Markdown (simulated) = SUM(fact_commercial_monthly[markdown_value_sim])
Markdown % of list (simulated) =
    DIVIDE([Markdown (simulated)], SUM(fact_commercial_monthly[list_revenue_sim]))
Units sold = SUM(fact_commercial_monthly[observed_units])            -- real: no suffix
Fulfilled units (simulated) = SUM(fact_commercial_monthly[fulfilled_units_sim])
Demand fulfilment % (simulated) = DIVIDE([Fulfilled units (simulated)], [Units sold])
OOS day rate % (simulated) =
    DIVIDE(SUM(fact_commercial_monthly[stockout_days_sim]), SUM(fact_commercial_monthly[days]))

-- Procurement
Procurement spend (simulated) = SUM(fact_procurement_monthly[po_value_sim])
On-time % (simulated) =
    DIVIDE(SUM(fact_procurement_monthly[on_time_lines_sim]), SUM(fact_procurement_monthly[po_lines]))
In-full % (simulated) =
    DIVIDE(SUM(fact_procurement_monthly[in_full_lines_sim]), SUM(fact_procurement_monthly[po_lines]))
PPV (simulated) = SUM(fact_procurement_monthly[ppv_total_sim])
PPV % of spend (simulated) = DIVIDE([PPV (simulated)], [Procurement spend (simulated)])
Avg lead time days (simulated) = AVERAGE(fact_procurement_monthly[avg_lead_time_days_sim])

-- Retail
Avg inventory value (simulated) = AVERAGE(fact_commercial_monthly[avg_inventory_value_sim])
Avg inventory units (simulated) = AVERAGE(fact_commercial_monthly[avg_inventory_units_sim])
Sell-through % (simulated) =
    DIVIDE([Fulfilled units (simulated)],
           [Fulfilled units (simulated)] + SUM(fact_commercial_monthly[unfulfilled_units_sim]))
```

**Every ratio uses `DIVIDE` on sums**, never an average of per-row percentages: a mean of
ratios lets a small denominator dominate the headline (docs/24 §2 shows the same figure
reading +206% instead of +52.3% when that rule is broken).

## 4. Pages

| Page | Visuals |
|---|---|
| **Executive** | six KPI cards (revenue, margin %, markdown %, spend, fulfilment %, OOS %); monthly revenue line; monthly margin % line **as a separate visual** — never a second y-axis on the revenue chart; top-10 families by revenue |
| **Pricing** | margin % by family (sorted bar); markdown % vs margin % scatter; uplift-gap bar from `dim_family_commercial[break_even_uplift_pct_sim]` against `[estimated_observational_uplift_pct]` |
| **Procurement** | spend by supplier; on-time % and in-full % grouped bar; price factor vs late rate scatter (the sourcing trade-off) |
| **Retail** | OOS day rate by family; lowest demand fulfilment; monthly average inventory value |

Slicers on every page: month range, sourcing group, store type.

## 5. Before publishing

- Put the provenance table on a final page, or in a tooltip on the Executive cards. A viewer
  must be able to find out that the money is modelled without reading the repo.
- Title the report *Commercial Cockpit — simulated commercial layer*.
- Nothing on the report may claim a real Favorita price, cost, margin, supplier or lost sale
  (docs/19 §6, docs/20 §6, docs/21 §7, docs/22 §6, docs/23 §5, docs/24 §7).
