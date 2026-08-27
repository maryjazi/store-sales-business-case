# 09 — Functional Requirements

**Version:** 1.0  

---

## 1. Scope

Functional requirements describe **what the system must do** — implemented primarily in `etl/`, `sql/`, `dashboard/`, and `tests/`.

---

## 2. Data ingestion & merge (FR-100)

| ID | Requirement | Priority | Implementation |
|---|---|---|---|
| FR-101 | Load all 6 raw CSV files with correct date parsing | Must | `etl/phase0_data_understanding.py` |
| FR-102 | Profile each source (shape, dtypes, missing, date range) | Must | phase0 `profile()` |
| FR-103 | Join train + stores on `store_nbr` (left join) | Must | phase0 |
| FR-104 | Join oil with daily forward/backward fill | Must | phase0 |
| FR-105 | Join transactions on date + store_nbr | Must | phase0 |
| FR-106 | Join national holidays with dedup by date | Must | phase0 |
| FR-107 | Save merged output as Parquet | Must | `merged_train.parquet` |
| FR-108 | Assert merged row count = train row count | Must | `tests/test_data_quality.py` |

---

## 3. Data cleaning & feature engineering (FR-200)

| ID | Requirement | Priority | Implementation |
|---|---|---|---|
| FR-201 | Fill missing transactions with 0; set `transactions_missing` flag | Must | `etl/phase1_cleaning_features.py` |
| FR-202 | Add calendar features (year, month, DOW, weekend, etc.) | Must | `etl/features.py` |
| FR-203 | Add `is_payday` (15th + month-end) | Must | `etl/features.py` |
| FR-204 | Add `days_since_store_open` lifecycle feature | Must | `etl/features.py` |
| FR-205 | Flag sales outliers (>99.9th pct per family) | Must | phase1 |
| FR-206 | Convert categoricals to `category` dtype | Should | phase1 |
| FR-207 | Build matching feature set for test.csv | Must | phase1 → `prepared_test.parquet` |
| FR-208 | Exclude `transactions` from test/forecast features | Must | phase1 (leakage guard) |

---

## 4. Exploratory analysis (FR-300)

| ID | Requirement | Priority | Implementation |
|---|---|---|---|
| FR-301 | Generate daily/weekly/monthly sales trend charts | Must | `etl/phase2_eda.py` |
| FR-302 | Analyze category and store-type breakdowns | Must | phase2 → figures 04–06 |
| FR-303 | Measure holiday, payday, weekend effects | Must | phase2 → figures 07–08 |
| FR-304 | Analyze oil price vs monthly sales | Should | phase2 → figure 09 |
| FR-305 | Export structured insights JSON | Must | `reports/eda_insights.json` |
| FR-306 | Save all charts to `reports/figures/` | Must | figures 01–09 |

---

## 5. KPI reporting (FR-400)

| ID | Requirement | Priority | Implementation |
|---|---|---|---|
| FR-401 | Compute headline KPIs (12 metrics) | Must | `etl/phase3_kpi_reporting.py` |
| FR-402 | Export store ranking CSV | Must | `kpi_store.csv` |
| FR-403 | Export category performance CSV | Must | `kpi_category.csv` |
| FR-404 | Export monthly trend CSV | Must | `kpi_monthly.csv` |
| FR-405 | Generate markdown KPI report | Must | `reports/kpi_report.md` |
| FR-406 | SQL equivalents for warehouse queries | Should | `sql/02–05` |

---

## 6. Forecasting (FR-500)

| ID | Requirement | Priority | Implementation |
|---|---|---|---|
| FR-501 | Hold out last 16 days for validation | Must | `etl/phase4_forecasting.py` |
| FR-502 | Compare ≥ 3 baseline models + LightGBM | Must | phase4 |
| FR-503 | Score with RMSLE | Must | phase4 |
| FR-504 | Export feature importance | Must | `reports/feature_importance.csv` |
| FR-505 | Save trained model artifact | Must | `lightgbm_model.txt` |
| FR-506 | Generate test-window forecasts | Must | `etl/phase4b_generate_forecast.py` |
| FR-507 | Export Kaggle submission format | Must | `reports/forecast_submission.csv` |

---

## 7. BI export & dashboard (FR-600)

| ID | Requirement | Priority | Implementation |
|---|---|---|---|
| FR-601 | Export fact_sales_actual (Parquet) | Must | `etl/phase5_powerbi_export.py` |
| FR-602 | Export fact_sales_forecast (Parquet) | Must | phase5 |
| FR-603 | Export dim_store, dim_date, dim_family (CSV) | Must | phase5 |
| FR-604 | Add `family_group` business grouping to dim_family | Should | phase5 |
| FR-605 | Document DAX measures and page layout | Must | `dashboard/POWERBI_GUIDE.md` |
| FR-606 | Support year/city/type/category slicers | Should | Dashboard design doc |
| FR-607 | Provide an interactive Streamlit dashboard reading the same KPI/star-schema outputs | Should | `dashboard/app.py` |

---

## 8. Testing & CI (FR-700)

| ID | Requirement | Priority | Implementation |
|---|---|---|---|
| FR-701 | Unit tests for feature engineering | Must | `tests/test_features.py` |
| FR-702 | Data quality tests on processed data | Must | `tests/test_data_quality.py` |
| FR-703 | Automated test run on GitLab CI | Must | `.gitlab-ci.yml` |
| FR-704 | Build and run the pipeline inside a Docker image as part of CI | Must | `Dockerfile`, `.gitlab-ci.yml` (`docker-build` stage) |
| FR-705 | Push the built image to the GitLab Container Registry on `main` | Should | `.gitlab-ci.yml` (`docker-push` stage) |

---

## 9. Acceptance criteria summary

| Module | Pass criteria |
|---|---|
| Merge | 3,000,888 rows, no duplicate ids |
| Features | `is_payday`, `days_since_store_open` present in cleaned data |
| KPIs | 12 headline KPIs in kpi_report.md |
| Forecast | RMSLE ≤ 0.47 internal; ≤ 0.50 Kaggle |
| Tests | All pytest cases pass |
| Dashboard data | 5 tables in dashboard/data/ |
| Docker image | Builds successfully and runs the pytest suite |

---

## 10. Related documents

- [02_Business_Requirements.md](02_Business_Requirements.md)
- [10_Non_Functional_Requirements.md](10_Non_Functional_Requirements.md)
- [15_ETL_Design.md](15_ETL_Design.md)
