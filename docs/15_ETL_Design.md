# 15 — ETL Design

**Version:** 1.0  
**Implementation:** `etl/` directory  

---

## 1. Pipeline overview

```
data/raw/*.csv
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 0: Data Understanding & Merge                    │
│  phase0_data_understanding.py                           │
│  Output: merged_train.parquet (3,000,888 × 15)          │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 1: Cleaning & Feature Engineering                │
│  phase1_cleaning_features.py + features.py            │
│  Output: cleaned_train.parquet, prepared_test.parquet   │
└──────┬──────────────────┬──────────────────┬──────────┘
       ▼                  ▼                  ▼
   Phase 2            Phase 3            Phase 4
   EDA                KPIs               Forecasting
   phase2_eda.py      phase3_kpi_        phase4_forecasting.py
                      reporting.py       phase4b_generate_forecast.py
       │                  │                  │
       ▼                  ▼                  ▼
   reports/figures/   reports/kpi_*     model + forecast CSV
       │                  │                  │
       └──────────────────┴──────────────────┘
                          ▼
                   Phase 5: BI Export
                   phase5_powerbi_export.py
                          ▼
                   dashboard/data/*
```

---

## 2. Phase specifications

### Phase 0 — Merge (`phase0_data_understanding.py`)

| Step | Operation | Input | Output |
|---|---|---|---|
| 0.1 | Load CSVs | 6 raw files | DataFrames |
| 0.2 | Profile sources | DataFrames | Console log |
| 0.3 | Join stores | train + stores | +city, state, type, cluster |
| 0.4 | Fill & join oil | oil → daily calendar | +dcoilwtico |
| 0.5 | Join transactions | +transactions.csv | +transactions (nullable) |
| 0.6 | Dedup & join holidays | national, non-transferred | +is_holiday |
| 0.7 | Save Parquet | merged DataFrame | merged_train.parquet |

**Error handling:** Row count assertion (must equal train rows)

---

### Phase 1 — Clean & Features (`phase1_cleaning_features.py`)

| Step | Operation | Details |
|---|---|---|
| 1.1 | Load merged_train | From phase 0 |
| 1.2 | Handle missing transactions | Fill 0 + flag |
| 1.3 | Add time features | `features.add_time_features()` |
| 1.4 | Add lifecycle features | `features.add_store_lifecycle_features()` |
| 1.5 | Flag outliers | 99.9th pct per family |
| 1.6 | Optimize dtypes | category dtype for strings |
| 1.7 | Process test.csv | Same features, no sales/transactions |
| 1.8 | Save outputs | cleaned_train + prepared_test |

**Shared module:** `etl/features.py` — ensures train/test parity

---

### Phase 2 — EDA (`phase2_eda.py`)

| Output | Chart |
|---|---|
| Daily trend | `01_daily_sales_trend.png` |
| Yearly/monthly | `02_yearly_monthly.png` |
| Day of week | `03_day_of_week.png` |
| Top families | `04_top_families.png` |
| Store type | `05_store_type.png` |
| Top cities | `06_top_cities.png` |
| Holiday effect | `07_holiday_effect.png` |
| Payday effect | `08_payday_effect.png` |
| Oil vs sales | `09_oil_vs_sales.png` |

Also writes `reports/eda_insights.json`

---

### Phase 3 — KPIs (`phase3_kpi_reporting.py`)

| Output | Content |
|---|---|
| kpi_report.md | Headline + store + category sections |
| kpi_summary.csv | Machine-readable headline KPIs |
| kpi_store.csv | Per-store rollup |
| kpi_category.csv | Per-family rollup |
| kpi_monthly.csv | Monthly trend |

---

### Phase 4 — Forecasting

**phase4_forecasting.py:**

| Step | Details |
|---|---|
| Load cleaned_train | ~3M rows |
| Split | Last 16 days = validation |
| Train baselines | Naive, same-weekday, 28-day MA |
| Train LightGBM | 900K sample; categorical features |
| Evaluate | RMSLE on validation |
| Save | model, val predictions, figures 10–12 |

**phase4b_generate_forecast.py:**

| Step | Details |
|---|---|
| Load model + prepared_test | |
| Predict | 28,512 rows |
| Clip | predictions ≥ 0 |
| Export | forecast_submission.csv, forecast_detail.parquet |

---

### Phase 5 — BI Export (`phase5_powerbi_export.py`)

| Output table | Source | Format |
|---|---|---|
| fact_sales_actual | cleaned_train | Parquet |
| fact_sales_forecast | forecast_detail | Parquet |
| dim_store | stores.csv | CSV |
| dim_date | derived calendar | CSV |
| dim_family | unique families + group | CSV |

---

## 3. Design patterns

| Pattern | Application |
|---|---|
| **Medallion (raw → processed → serve)** | raw CSV → parquet → dashboard |
| **Shared transform module** | `features.py` for train/test parity |
| **Write-local-copy-remote** | phase0 writes to /tmp then copies (performance) |
| **Idempotent phases** | Each phase overwrites its outputs on re-run |
| **Phase isolation** | Each script runnable independently given prior outputs |
| **Containerized packaging** | `Dockerfile` + GitLab CI `docker-build`/`docker-push` stages for reproducible runs |

---

## 3a. Schema contracts and shared audits

Two defects taught this pipeline the same lesson twice: a number can be wrong in a file long
before anyone notices, if the documentation, the writing code and the file on disk each hold
their own idea of the truth.

- `observed_units` was written as float32 while docs/21 declared float64. A float32 × float32
  product in pandas stays float32, so a revenue reconciliation two phases later silently lost
  the precision it depended on.
- A margin bridge stopped adding up because `NaN` effects met a skipna sum.

The answer in both cases is the same: **one declaration, enforced on the way out and
validated on the way in.**

| Module | Owns | Used by |
|---|---|---|
| `etl/schema.py` | column names, order and dtypes of all 12 phase 6–9 outputs; `write_table` enforces before persisting, `read_table` validates after reading | phases 6–9, `tests/test_schema_contract.py` |
| `etl/audit.py` | the reconciliations that must hold: inventory lineage, revenue views, margin bridge | phases 8–9, `tests/test_inventory_layer.py`, `tests/test_pricing_layer.py`, `tests/test_pipeline_audits.py` |

The ETL scripts and the test suite call the **same** implementation. A test that
re-implements the formula it is checking ends up certifying its own arithmetic, so instead
`tests/test_pipeline_audits.py` proves the audits are not vacuous by feeding them
deliberately broken frames and requiring them to raise.

`schema.LINEAGE_COLUMNS` marks the columns that carry an audit chain; narrowing one of them
is reported as a contract violation, which is exactly the defect that started this.

**Known technical debt.** Quantities would be safer as fixed-point `int64` milli-units, which
would let the inventory equation close exactly instead of within a tolerance. That migration
touches phases 6–9, the tests and the reports, so it is tracked as future hardening rather
than folded into a structural refactor.

---

## 4. SQL parallel path

Warehouse-native queries in `sql/` replicate phase 0 merge and phase 3 KPIs for teams preferring SQL over Python.

---

## 5. Testing integration

| Test | Phase covered |
|---|---|
| test_merged_row_count | Phase 0 |
| test_merged_has_no_duplicate_ids | Phase 0 |
| test_cleaned_has_engineered_columns | Phase 1 |
| test_add_time_features_payday | features.py |
| test_add_store_lifecycle_features | features.py |

CI runs via `.gitlab-ci.yml`

---

## 6. Operational runbook

```bash
# Full pipeline
python etl/phase0_data_understanding.py
python etl/phase1_cleaning_features.py
python etl/phase2_eda.py
python etl/phase3_kpi_reporting.py
python etl/phase4_forecasting.py
python etl/phase4b_generate_forecast.py
python etl/phase5_powerbi_export.py
pytest tests/ -v

# Or run the test suite inside Docker (same environment as CI)
docker build -t sales-forecast .
docker run --rm -v "$(pwd)/data:/app/data" sales-forecast
```

---

## 7. Related documents

- [docs/pipeline.md](pipeline.md)
- [docs/architecture.md](architecture.md)
- [07_Data_Requirements.md](07_Data_Requirements.md)
- [16_Data_Model.md](16_Data_Model.md)
