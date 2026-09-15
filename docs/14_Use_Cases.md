# 14 — Use Cases

**Version:** 1.0  

---

## UC-01 — Executive reviews monthly sales performance

| Field | Value |
|---|---|
| **Actor** | Retail Operations Director |
| **Goal** | Understand whether the chain is growing and where volume is concentrated |
| **Preconditions** | KPI pipeline has run; dashboard is published |
| **Trigger** | Monthly business review meeting |

### Main flow

1. Director opens Power BI Overview page
2. Reviews KPI cards: Total Sales, Avg Daily Sales, YoY Growth
3. Drills into category treemap — confirms top 3 = 64% of unit sales
4. Filters by year to compare 2015 vs 2016 growth (+15% → +19.8%)
5. Notes decelerating growth trend for forward planning

### Postconditions

- Growth narrative confirmed with data
- Category concentration risk flagged for merchandising follow-up

### Implementation

- KPIs: `06_KPI_Definition.md` KPI-01 – KPI-05
- Dashboard: Overview page (`17_Dashboard_Design.md`)
- Data: `fact_sales_actual`, `dim_date`, `dim_family`

---

## UC-02 — Merchandising plans holiday inventory

| Field | Value |
|---|---|
| **Actor** | Merchandising Manager |
| **Goal** | Increase stock for national holidays based on measured uplift |
| **Preconditions** | Holiday uplift KPI computed (+19%) |
| **Trigger** | Upcoming national holiday calendar |

### Main flow

1. Manager opens External Factors dashboard page
2. Reviews Holiday Uplift % measure (+19.0%)
3. Filters by top categories (Grocery I, Beverages, Produce)
4. Adjusts replenishment orders for holiday window
5. Cross-checks weekend uplift (+39%) for staffing coordination with Ops

### Alternate flow

- **4a.** Category-level holiday effect not available in v1 → uses aggregate uplift with safety buffer

### Postconditions

- Holiday inventory plan updated
- Staffing calendar aligned with Ops

---

## UC-03 — Supply chain generates demand forecast

| Field | Value |
|---|---|
| **Actor** | Supply Chain / Inventory Lead |
| **Goal** | Obtain 16-day store × category demand forecast |
| **Preconditions** | Model trained; `prepared_test.parquet` available |
| **Trigger** | Weekly replenishment cycle |

### Main flow

1. Analyst runs `etl/phase4b_generate_forecast.py`
2. System loads saved LightGBM model and scores test features
3. Forecast exported to `reports/forecast_submission.csv` and `forecast_detail.parquet`
4. Supply chain imports forecast into replenishment system
5. Compares forecast total to 28-day moving average baseline

### Postconditions

- 28,512 predictions available (54 × 33 × 16)
- Forecast accuracy tracked via RMSLE (0.465 internal, 0.48464 Kaggle)

### Business rules

- BR-FC01: 16-day horizon
- BR-C06: No transaction features in model

---

## UC-04 — Regional manager reviews store performance fairly

| Field | Value |
|---|---|
| **Actor** | Regional Store Manager |
| **Goal** | Identify underperforming stores without penalizing new openings |
| **Preconditions** | Store KPI CSV and lifecycle feature available |
| **Trigger** | Quarterly performance review |

### Main flow

1. Manager opens Store Performance dashboard page
2. Reviews store ranking table sorted by Total Sales
3. Notices store 52 (Manta) at bottom — checks `days_since_store_open`
4. Compares per-day average since opening vs peer Type A stores
5. Escalates genuine underperformers; excludes lifecycle artifacts

### Postconditions

- Fair performance conversation documented
- No punitive action on store 52 based on raw total alone

---

## UC-05 — Data analyst runs full ETL pipeline

| Field | Value |
|---|---|
| **Actor** | Data Analyst |
| **Goal** | Regenerate all artifacts from raw Kaggle CSVs |
| **Preconditions** | Raw CSVs in `data/raw/`; Python env configured |
| **Trigger** | New data refresh or code change |

### Main flow

1. Analyst runs phases 0 → 5 sequentially (`docs/pipeline.md`)
2. Phase 0 merges sources; asserts 3,000,888 rows
3. Phase 1 engineers features; produces cleaned_train + prepared_test
4. Phases 2–3 generate EDA and KPI outputs
5. Phase 4 trains model; phase 4b scores test set
6. Phase 5 exports dashboard star schema
7. Analyst runs `pytest tests/ -v` to verify

### Postconditions

- All processed files and reports regenerated
- CI tests pass

---

## UC-06 — Analyst investigates promotion effectiveness

| Field | Value |
|---|---|
| **Actor** | Merchandising Manager + Data Analyst |
| **Goal** | Understand which categories benefit most from promotions |
| **Preconditions** | Category KPI with promo uplift computed |
| **Trigger** | Promo budget planning season |

### Main flow

1. Analyst opens `data/processed/kpi_category.csv`
2. Reviews promo uplift by family (e.g. School Supplies +4257%)
3. Reads caveat: correlational, low non-promo baseline inflates ratio
4. Recommends controlled category-level analysis as next phase
5. Manager uses ranking to prioritize promo categories, not raw multiplier

### Postconditions

- Promo budget discussion informed by data with documented limitations

---

## Use case traceability matrix

| Use case | Business req | Functional req | KPI | Dashboard page |
|---|---|---|---|---|
| UC-01 | BG-05 | FR-401 | KPI-01–05 | Overview |
| UC-02 | BG-02 | FR-303 | KPI-06–07 | External Factors |
| UC-03 | BG-04 | FR-501–507 | KPI-12 | Forecast |
| UC-04 | BG-01 | FR-402 | KPI-S01–04 | Store Performance |
| UC-05 | BG-01 | FR-101–703 | All | N/A |
| UC-06 | BG-02 | FR-403 | KPI-C04 | Category & Region |

---

## Related documents

- [02_Business_Requirements.md](02_Business_Requirements.md)
- [03_Stakeholders.md](03_Stakeholders.md)
- [17_Dashboard_Design.md](17_Dashboard_Design.md)
