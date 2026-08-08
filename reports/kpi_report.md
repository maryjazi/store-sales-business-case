# KPI Report — Store Sales Business Case

Source: `data/processed/cleaned_train.parquet` (2013-01-01 to 2017-08-15). Full detail tables: `reports/kpi_summary.csv`, `data/processed/kpi_store.csv`, `kpi_category.csv`, `kpi_monthly.csv`.

## 1. Headline KPIs

| KPI | Value | Definition |
|---|---|---|
| Total Sales | $1.07B | Sum of `sales` across all stores/categories/days in the training window |
| Avg Daily Sales | $637.6K | Total sales ÷ number of distinct days |
| YoY Growth 2013→2014 | +49.2% | (2014 total ÷ 2013 total) − 1 |
| YoY Growth 2014→2015 | +15.0% | Same, 2015 vs 2014 |
| YoY Growth 2015→2016 | +19.8% | Same, 2016 vs 2015 (2017 excluded — partial year in the data) |
| Weekend Sales Uplift | +39.3% | Avg row sales, weekend vs weekday |
| National Holiday Uplift | +19.0% | Avg row sales, national holiday vs regular day |
| Payday Uplift (15th/month-end) | +1.4% | Avg row sales, payday vs regular day |
| Oil Price ↔ Monthly Sales Correlation | −0.75 | Pearson correlation, monthly totals |
| Avg Sales per Transaction | $7.46 | Ticket-size proxy: sales ÷ transactions, store-days with recorded transactions |
| % Rows with Zero Sales | 31.3% | Data quality / demand-coverage indicator |
| % Rows Missing Transaction Data | 8.2% (pre-fill) | Filled with 0 in Phase 1; flagged via `transactions_missing` |

## 2. Store Performance

**Top 5 stores by total sales** — all in Quito, all high-volume urban locations:

| Store | City | Type | Total Sales |
|---|---|---|---|
| 44 | Quito | A | $62.1M |
| 45 | Quito | A | $54.5M |
| 47 | Quito | A | $50.9M |
| 3 | Quito | D | $50.5M |
| 49 | Quito | A | $43.4M |

**Bottom 5 stores by total sales:**

| Store | City | Type | Total Sales |
|---|---|---|---|
| 35 | Playas | C | $7.7M |
| 30 | Guayaquil | C | $7.4M |
| 32 | Guayaquil | C | $6.0M |
| 22 | Puyo | C | $4.1M |
| 52 | Manta | A | $2.7M |

Store 52's low total is partly a lifecycle artifact, not pure underperformance — Phase 1 showed it started operating partway through the data window (see `days_since_store_open`). Its per-day average since opening should be used for any manager-facing comparison, not the raw total. Full ranking: `data/processed/kpi_store.csv`.

## 3. Category Performance

Full table: `data/processed/kpi_category.csv` (columns: total sales, share %, average promo uplift per category).

Top promo-uplift categories (avg sales on promoted rows vs non-promoted rows):

| Category | Promo Uplift |
|---|---|
| School and Office Supplies | +4257% |
| Baby Care | +1415% |
| Pet Supplies | +352% |
| Home and Kitchen II | +301% |
| Produce | +208% |

**Caveat:** these are large because the categories have very low non-promo baselines (e.g. school supplies barely sell outside back-to-school promo periods) — read as "promotions matter a lot for these categories," not as a literal always-on multiplier. A controlled/causal estimate is planned for Phase 4 modeling.

## 4. Monthly Trend

`data/processed/kpi_monthly.csv` — total sales, average oil price, holiday count, and YoY growth % per month. Feeds directly into the Power BI trend visuals in Phase 5.

## 5. Forecast Accuracy

*Placeholder — filled in after Phase 4 (forecasting model), reported as RMSLE (the competition's evaluation metric) and, where useful, MAPE for business interpretability.*
