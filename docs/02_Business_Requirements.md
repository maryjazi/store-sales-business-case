# 02 — Business Requirements

**Document ID:** BR-001  
**Version:** 1.0  
**Status:** Approved  

---

## 1. Overview

This document captures the business requirements for the Store Sales Analytics & Forecasting initiative. Requirements are derived from retail operations needs: understanding what drives sales, monitoring performance, and predicting future demand.

## 2. Business goals

| ID | Goal | Priority |
|---|---|---|
| BG-01 | Understand historical sales patterns across stores, categories, and regions | Must have |
| BG-02 | Quantify impact of calendar events (weekends, holidays, paydays) on demand | Must have |
| BG-03 | Quantify relationship between external factors (oil price) and sales | Should have |
| BG-04 | Build a forecasting model that outperforms manual/simple planning methods | Must have |
| BG-05 | Define a KPI set for recurring executive and operational reporting | Must have |
| BG-06 | Provide self-service monitoring via an interactive dashboard | Should have |
| BG-07 | Deliver actionable recommendations for inventory, staffing, and promotions | Must have |

## 3. Functional business requirements

### 3.1 Sales analytics

| ID | Requirement | Acceptance criteria |
|---|---|---|
| BR-01 | System shall aggregate sales by day, store, category, city, and store type | Aggregations match manual checks on raw data |
| BR-02 | System shall compute year-over-year growth by year | YoY values: +49.2% (2013→2014), +15.0%, +19.8% |
| BR-03 | System shall measure weekend vs weekday sales uplift | Uplift ≈ +39% documented |
| BR-04 | System shall measure national holiday sales uplift | Uplift ≈ +19% documented |
| BR-05 | System shall rank stores by total and average sales | Ranking exported to `kpi_store.csv` |
| BR-06 | System shall rank categories by revenue share | Top 3 = 64% of total sales |

### 3.2 Forecasting

| ID | Requirement | Acceptance criteria |
|---|---|---|
| BR-07 | System shall forecast daily sales for each store × category for 16-day horizon | 28,512 predictions generated |
| BR-08 | Model shall be validated without data leakage | Time-based hold-out: last 16 days of train |
| BR-09 | Model shall beat best naive baseline | LightGBM RMSLE 0.465 vs MA baseline 0.522 |
| BR-10 | Forecast accuracy shall be verified externally | Kaggle RMSLE 0.48464 |

### 3.3 Reporting & dashboard

| ID | Requirement | Acceptance criteria |
|---|---|---|
| BR-11 | System shall produce executive KPI summary | `reports/kpi_report.md`, `kpi_summary.csv` |
| BR-12 | System shall export BI-ready star schema | 2 fact + 3 dimension tables in `dashboard/data/` |
| BR-13 | Dashboard shall support filtering by year, city, store type, category group | Slicers defined in `17_Dashboard_Design.md` |
| BR-14 | Dashboard shall show actual vs forecast trend | Combined line chart on Overview page |

### 3.4 Data quality

| ID | Requirement | Acceptance criteria |
|---|---|---|
| BR-15 | Missing transaction counts shall be handled explicitly | Filled with 0; `transactions_missing` flag retained |
| BR-16 | Duplicate holiday records shall not inflate row counts | Merge output = 3,000,888 rows |
| BR-17 | Store lifecycle shall be accounted for in analysis | `days_since_store_open` feature engineered |
| BR-18 | Extreme sales values shall be flagged, not silently removed | `sales_outlier_flag` on top 0.1% per family |

## 4. Reporting requirements

| Report | Audience | Frequency | Format |
|---|---|---|---|
| KPI summary | Executive leadership | Monthly | Markdown + CSV + Power BI |
| Store performance ranking | Regional managers | Monthly | CSV + dashboard table |
| Category performance | Merchandising | Monthly | CSV + dashboard charts |
| Forecast vs actual | Operations planning | Daily (forward) / Weekly (review) | CSV + dashboard |
| Business case | Stakeholders / portfolio | Once (project completion) | Markdown |

## 5. Constraints on requirements

- Historical data only through 2017-08-15 for training; forecast horizon 2017-08-16 → 2017-08-31
- Raw data cannot be redistributed (Kaggle competition rules)
- `transactions` is available historically but not at forecast time — excluded from model features

## 6. Traceability

| Business requirement | Implemented in | Verified by |
|---|---|---|
| BR-01 – BR-06 | `etl/phase2_eda.py`, `phase3_kpi_reporting.py` | EDA figures, KPI report |
| BR-07 – BR-10 | `etl/phase4_forecasting.py`, `phase4b_generate_forecast.py` | Model comparison JSON, Kaggle score |
| BR-11 – BR-14 | `etl/phase3_kpi_reporting.py`, `phase5_powerbi_export.py` | KPI files, dashboard data |
| BR-15 – BR-18 | `etl/phase0_data_understanding.py`, `phase1_cleaning_features.py` | README data notes, tests |

## 7. Related documents

- [06_KPI_Definition.md](06_KPI_Definition.md)
- [09_Functional_Requirements.md](09_Functional_Requirements.md)
- [14_Use_Cases.md](14_Use_Cases.md)
