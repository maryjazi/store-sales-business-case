# 01 — Project Charter

| Field | Value |
|---|---|
| **Project name** | Store Sales Analytics & Demand Forecasting |
| **Organization** | Corporación Favorita (Ecuador) — simulated via Kaggle competition dataset |
| **Project owner** | Retail Operations & Merchandising Leadership |
| **Project lead / analyst** | Maryam |
| **Version** | 1.0 |
| **Date** | August 2026 |
| **Status** | Completed (analytics, forecasting, containerization & CI/CD); Power BI dashboard build in progress, Streamlit dashboard complete |

---

## 1. Purpose

Establish an analytical foundation for a 54-store retail chain to understand sales drivers, monitor business KPIs, and forecast daily demand at store × product-category level — enabling better inventory, staffing, and promotional planning.

## 2. Problem statement

Retail chains lose margin when demand is mispredicted: overstocking ties up capital and increases waste; understocking loses sales and customer trust. With 33 product categories across 54 locations, demand is shaped by store-specific factors, calendar effects, promotions, and macro conditions (e.g. oil price in Ecuador's economy). Leadership lacks a unified, repeatable analytics and forecasting capability.

## 3. Project scope

### In scope

- Merge and profile six raw data sources into a single analytical dataset
- Data cleaning, feature engineering, and documented business rules
- Exploratory sales analytics (trend, seasonality, category, region, external factors)
- KPI definition and recurring reporting outputs
- Demand forecasting model with honest baseline comparison
- Power BI star-schema export and dashboard design guide
- Interactive Streamlit dashboard as a lightweight, no-install alternative to Power BI
- Containerization (Docker) with automated build/test in GitLab CI/CD
- Business case with quantified findings and recommendations
- Project documentation (`docs/`, `sql/`, `tests/`, CI)

### Out of scope

- Real-time streaming ingestion or production MLOps deployment
- Causal promotion-ROI modeling (identified as next phase)
- Per-store-cluster custom models
- Redistribution of raw Kaggle data (competition rules)

## 4. Deliverables

| # | Deliverable | Location |
|---|---|---|
| 1 | Cleaned analytical dataset | `data/processed/` |
| 2 | ETL pipeline (7 phases) | `etl/` |
| 3 | KPI report & CSV exports | `reports/`, `data/processed/kpi_*.csv` |
| 4 | Forecasting model & submission | `data/processed/lightgbm_model.txt`, `reports/forecast_submission.csv` |
| 5 | EDA figures & insights | `reports/figures/`, `reports/eda_insights.json` |
| 6 | Power BI data model | `dashboard/data/` |
| 7 | Business case report | `reports/business_case.md` |
| 8 | Project documentation pack | `docs/` |
| 9 | Docker image + CI/CD pipeline | `Dockerfile`, `.gitlab-ci.yml` |
| 10 | Streamlit dashboard | `dashboard/app.py` |

## 5. Success criteria

| Criterion | Target | Actual |
|---|---|---|
| Single merged dataset with no row inflation | 3,000,888 rows | ✅ 3,000,888 |
| Forecast beats best simple baseline | > 5% RMSLE improvement | ✅ 11% (0.465 vs 0.522) |
| External validation on Kaggle leaderboard | RMSLE < 0.50 | ✅ 0.48464 |
| KPI framework documented & exportable | ≥ 10 headline KPIs | ✅ 12 KPIs |
| Reproducible pipeline | Full run from raw CSVs | ✅ Documented in `docs/pipeline.md` |
| Dashboard data model ready | Star schema exported | ✅ 2 facts + 3 dims |
| Interactive dashboard runs without a desktop BI tool | Streamlit app loads and renders all charts | ✅ Verified headless (`streamlit.testing.v1.AppTest`) |
| Pipeline runs identically outside the host machine | `docker build` + `docker run` complete pytest suite | ✅ Verified — 3/3 pass (no data mount), 6/6 pass (data volume-mounted) |

## 6. Timeline (high level)

| Phase | Activity | Duration |
|---|---|---|
| 0 | Data understanding & merge | Week 1 |
| 1 | Cleaning & feature engineering | Week 1–2 |
| 2 | Exploratory analysis | Week 2 |
| 3 | KPI reporting | Week 3 |
| 4 | Forecasting model | Week 3–4 |
| 5 | Power BI export & dashboard | Week 4–5 |
| 6 | Business case & documentation | Week 5–6 |

## 7. Budget & resources

- **Compute:** Local Python environment (2-core sandbox for model training; full retrain recommended on standard hardware)
- **Tools:** Python 3.10+, Power BI Desktop (free), Docker, GitLab CI, Streamlit
- **Data:** Kaggle competition dataset (free with account)
- **Team:** 1 data analyst / data scientist (project lead)

## 8. Approval

| Role | Name | Sign-off |
|---|---|---|
| Project sponsor | Retail Operations Leadership | ☐ |
| Project lead | Maryam | ☑ (deliverables complete) |
| Data governance | — | N/A (academic/portfolio project) |

## 9. Related documents

- [02_Business_Requirements.md](02_Business_Requirements.md)
- [18_Project_Roadmap.md](18_Project_Roadmap.md)
- [reports/business_case.md](../reports/business_case.md)
