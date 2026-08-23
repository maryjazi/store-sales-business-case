# Architecture

## Overview

Store Sales Analytics & Forecasting is a batch analytics pipeline built on the [Kaggle Store Sales](https://www.kaggle.com/competitions/store-sales-time-series-forecasting) dataset. It follows a classic **medallion-style** flow: raw CSVs → cleaned Parquet → analytical reports → BI star schema.

```mermaid
flowchart LR
    subgraph raw [data/raw]
        CSV[Kaggle CSVs]
    end

    subgraph etl [etl/]
        P0[phase0 merge]
        P1[phase1 clean + features]
        P2[phase2 EDA]
        P3[phase3 KPIs]
        P4[phase4 forecast]
        P5[phase5 BI export]
    end

    subgraph processed [data/processed]
        PQ[Parquet + model]
    end

    subgraph outputs [reports/ + dashboard/]
        RPT[Markdown + figures]
        BI[Star schema tables]
    end

    CSV --> P0 --> PQ
    PQ --> P1 --> PQ
    PQ --> P2 --> RPT
    PQ --> P3 --> RPT
    PQ --> P4 --> RPT
    PQ --> P5 --> BI
```

## Layer responsibilities

| Layer | Folder | Role |
|---|---|---|
| **Raw** | `data/raw/` | Immutable Kaggle source files (not committed) |
| **ETL** | `etl/` | Python batch jobs — one script per phase, run in order |
| **Processed** | `data/processed/` | Intermediate and final analytical datasets |
| **SQL** | `sql/` | Equivalent analytical queries for warehouse / BI tools |
| **Reports** | `reports/` | Human-readable outputs, charts, submission file |
| **Dashboard** | `dashboard/` | Power BI star-schema export + build guide |
| **Tests** | `tests/` | Unit and data-quality checks |
| **CI** | `.gitlab-ci.yml` | Automated test stage on every push |

## Design principles

1. **Reproducibility** — every artifact in `data/processed/` and `reports/` can be regenerated from raw data by running the ETL scripts in order.
2. **No leakage** — `transactions` is excluded from the forecast feature set because it is not known at prediction time.
3. **Documented cleaning** — missing values, outliers, and holiday deduplication are flagged or filled with explicit rationale (see README Data Notes).
4. **Separation of concerns** — shared feature logic lives in `etl/features.py`; each phase script owns one step of the pipeline.

## External dependencies

- **Python 3.10+** with pandas, LightGBM, matplotlib
- **Power BI Desktop** (local) for dashboard build — data export is automated, `.pbix` is built manually
