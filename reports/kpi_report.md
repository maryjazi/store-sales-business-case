# KPI Report — Store Sales Business Case

Source: `data/processed/cleaned_train.parquet` (2013-01-01 to 2017-08-15). Full detail tables: `reports/kpi_summary.csv`, `data/processed/kpi_store.csv`, `kpi_category.csv`, `kpi_monthly.csv`.

## 1. Headline KPIs

> **Unit semantics:** `sales` is a quantity, not a currency amount (15.4% of values are fractional — weighed goods; no price column in the dataset). All volume figures below are in **units**.

| KPI | Value | Definition |
|---|---|---|
| Total Unit Sales | 1.07B units | Sum of `sales` across all stores/categories/days in the training window |
| Avg Daily Unit Sales | 637.6K units | Total unit sales ÷ number of distinct days |
| YoY Growth 2013→2014 | +49.2% | (2014 total ÷ 2013 total) − 1 |
| YoY Growth 2014→2015 | +15.0% | Same, 2015 vs 2014 |
| YoY Growth 2015→2016 | +19.8% | Same, 2016 vs 2015 (2017 excluded — partial year in the data) |
| Weekend Sales Uplift | +39.3% | Avg row sales, weekend vs weekday |
| National Holiday Uplift | +19.0% | Avg row sales, national holiday vs regular day |
| Payday Uplift (15th/month-end) | +1.4% | Avg row sales, payday vs regular day |
| Oil Price ↔ Monthly Sales Correlation | −0.75 | Pearson correlation, monthly totals |
| Avg Units per Transaction | 7.46 units | Basket-size proxy: unit sales ÷ transactions, store-days with recorded transactions |
| % Rows with Zero Sales | 31.3% | Data quality / demand-coverage indicator |
| % Rows Missing Transaction Data | 8.2% (pre-fill) | Filled with 0 in Phase 1; flagged via `transactions_missing` |

## 2. Store Performance

**Top 5 stores by total unit sales** — all in Quito, all high-volume urban locations:

| Store | City | Type | Total Unit Sales |
|---|---|---|---|
| 44 | Quito | A | 62.1M units |
| 45 | Quito | A | 54.5M units |
| 47 | Quito | A | 50.9M units |
| 3 | Quito | D | 50.5M units |
| 49 | Quito | A | 43.4M units |

**Bottom 5 stores by total unit sales:**

| Store | City | Type | Total Unit Sales |
|---|---|---|---|
| 35 | Playas | C | 7.7M units |
| 30 | Guayaquil | C | 7.4M units |
| 32 | Guayaquil | C | 6.0M units |
| 22 | Puyo | C | 4.1M units |
| 52 | Manta | A | 2.7M units |

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

**Caveat:** these are large because the categories have very low non-promo baselines (e.g. school supplies barely sell outside back-to-school promo periods) — read as "promotions matter a lot for these categories," not as a literal always-on multiplier. A controlled/causal estimate needs a matched-baseline design and is tracked as a separate promotion-effectiveness analysis — it is not covered by the forecasting phase.

## 4. Monthly Trend

`data/processed/kpi_monthly.csv` — total sales, average oil price, holiday count, and YoY growth % per month. Feeds directly into the Power BI trend visuals in Phase 5.

## 5. Forecast Accuracy

| Model | RMSLE (16-day validation) |
|---|---|
| Naive last-value | 0.660 |
| Same-weekday average (4 weeks) | 0.531 |
| 28-day moving average | 0.522 |
| **LightGBM (engineered features)** | **0.465** |

LightGBM beats the strongest baseline (28-day moving average) by ~11%. The same model was submitted to the Kaggle leaderboard on the competition's own held-out test window and scored **RMSLE 0.48464** — close to the internal validation estimate, which supports the time-based split as a fair test. Sources: `reports/model_comparison.json`, `reports/forecast_submission.csv`.
