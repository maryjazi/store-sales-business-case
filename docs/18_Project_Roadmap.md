# 18 — Project Roadmap

**Version:** 1.0  
**Last updated:** August 2026  

---

## 1. Phase summary (completed)

| Phase | Name | Deliverables | Status |
|---|---|---|---|
| 0 | Data Understanding | merged_train.parquet, profiling | ✅ Done |
| 1 | Cleaning & Features | cleaned_train, prepared_test | ✅ Done |
| 2 | Exploratory Analysis | figures 01–09, eda_insights.json | ✅ Done |
| 3 | KPI Reporting | kpi_report.md, kpi_*.csv | ✅ Done |
| 4 | Forecasting | LightGBM model, RMSLE 0.465 | ✅ Done |
| 4b | Forecast Generation | forecast_submission.csv, Kaggle 0.48464 | ✅ Done |
| 5 | Power BI Export | dashboard/data star schema | ✅ Done |
| 6 | Business Case | reports/business_case.md | ✅ Done |
| 7 | Documentation & CI | docs/, sql/, tests/, .gitlab-ci.yml, Dockerfile, Streamlit dashboard | ✅ Done |

---

## 1b. Track 2 — Commercial analytics (in progress)

Scope locked: pricing, profitability, retail/merchandising, inventory, procurement, supplier and
promotion analytics on the same sales history, using the simulation layer documented in
[19_Simulation_Design.md](19_Simulation_Design.md).

| Step | Name | Script | Status |
|---|---|---|---|
| B1 | Commercial Simulation Layer | `phase6_simulation_layer.py` | ✅ Done |
| B6 | Procurement & Supplier Foundation | `phase7_procurement.py` | ✅ Done |
| B4 | Inventory & Merchandising | `phase8_inventory.py` | ✅ Done |
| B2 | Pricing & Profitability | `phase9_pricing.py` | ✅ Done |
| B3 | Break-even & Price Sensitivity | `phase10_price_sensitivity.py` | ✅ Done |
| B5 | Promotion Effectiveness | `phase11_promotion.py` | ☐ Next |
| B7 | Scenario Analysis | `phase12_scenario.py` | ☐ Not started |
| B8 | Commercial Cockpit | `phase13_commercial_export.py` | ☐ Not started |

---

## 2. Timeline (actual)

```
Week 1   ████ Phase 0–1 (merge, clean, features)
Week 2   ████ Phase 2 (EDA)
Week 3   ████ Phase 3–4 (KPIs, forecasting)
Week 4   ████ Phase 4b–5 (forecast export, BI data)
Week 5   ████ Phase 6 (business case)
Week 6   ████ Phase 7 (docs pack, tests, CI, dashboard screenshots)
```

---

## 3. Current status & remaining items

| Item | Priority | Status | Owner |
|---|---|---|---|
| Power BI dashboard rebuild — 4 pages were built in a Power BI Desktop session that was never saved (window title `Untitled`); no `.pbix` exists in the repo | P1 | 🟡 Open | Analyst |
| Dashboard screenshots (External Factors, Forecast) | P2 | 🟡 Pending | Analyst |
| Full-data model retrain (2.97M rows) | P2 | ☐ Not started | Analyst |
| GitHub repo publish + portfolio links | P2 | ☐ Pending | Analyst |
| `docker build` / `docker run` verified locally (6/6 tests pass with data mounted) | P1 | ✅ Done | Analyst |
| Push to GitLab; confirm CI `docker-build` job is green | P1 | 🟡 Pending | Analyst |
| Streamlit dashboard (`dashboard/app.py`) | — | ✅ Done (tested headless) | Analyst |

---

## 4. Future roadmap (v2+)

### Q4 2026 — Model & analytics enhancements

| Initiative | Description | Effort |
|---|---|---|
| Full-data retrain | Train LightGBM on complete 2.97M rows | 1 day |
| Category-level payday analysis | Break aggregate +1.4% into per-family | 2 days |
| Causal promotion ROI | Matched/control comparison per category | 1 week |
| Store-cluster models | Separate models per cluster 1–17 | 1 week |

### Q1 2027 — Production readiness

| Initiative | Description | Effort |
|---|---|---|
| Warehouse deployment | Load star schema to BigQuery/Snowflake | 1 week |
| Scheduled ETL | GitLab scheduled pipeline or Airflow DAG | 3 days |
| Model monitoring | Rolling RMSLE dashboard + alert | 3 days |
| Automated Power BI refresh | Cloud gateway + scheduled refresh | 2 days |

### Q2 2027 — Business expansion

| Initiative | Description | Effort |
|---|---|---|
| Item/SKU-level analysis | Requires new data source | TBD |
| Promotion metadata integration | Campaign ID, discount % | TBD |
| Weather data by city | External API join | 3 days |
| What-if scenario slicers | Power BI parameters for promo/holiday | 1 week |

---

## 5. Milestone gates

| Milestone | Criteria | Target | Status |
|---|---|---|---|
| M1 — Data ready | merged + cleaned parquet validated | Week 2 | ✅ |
| M2 — Insights delivered | EDA + KPI report approved | Week 3 | ✅ |
| M3 — Model validated | RMSLE < 0.50 on Kaggle | Week 4 | ✅ (0.48464) |
| M4 — Dashboard live | 4 pages + 4 screenshots | Week 6 | 🟡 `.pbix` not saved; 2/4 screenshots exist; Streamlit alternative fully working |
| M5 — Portfolio complete | GitHub + README + business case | Week 6 | 🟡 Links pending |

---

## 6. Success metrics (post go-live)

| Metric | Baseline | Target (6 months) |
|---|---|---|
| Forecast RMSLE | 0.465 | < 0.45 (after full retrain) |
| Dashboard adoption | 0 users | 5+ stakeholders monthly |
| Manual report hours | ~8 hrs/month | < 2 hrs/month |
| Zero-sales rate (top 3 categories) | 31.3% chain-wide | < 28% |

---

## 7. Dependencies & blockers

| Blocker | Impact | Resolution |
|---|---|---|
| Power BI Desktop required for dashboard | Cannot automate .pbix | Manual build per guide |
| Kaggle data license | Cannot share raw CSVs | Processed outputs + download docs |
| 2-core training limit | Suboptimal model accuracy | Full retrain on better hardware |

---

## 8. Related documents

- [01_Project_Charter.md](01_Project_Charter.md)
- [13_Risk_Assessment.md](13_Risk_Assessment.md)
- [README.md](../README.md) — Project Phases table
