# SQL Analytics

SQL equivalents of key ETL and KPI logic. Assumes raw Kaggle tables are loaded into a warehouse with the same column names.

| Script | Purpose |
|---|---|
| [01_merge_raw_data.sql](01_merge_raw_data.sql) | Replicate phase0 merge (stores, oil, transactions, holidays) |
| [02_kpi_headline.sql](02_kpi_headline.sql) | Executive headline KPIs |
| [03_kpi_store_ranking.sql](03_kpi_store_ranking.sql) | Store-level sales ranking |
| [04_kpi_category.sql](04_kpi_category.sql) | Category (family) performance |
| [05_monthly_trend.sql](05_monthly_trend.sql) | Monthly sales and YoY growth |

Compatible with PostgreSQL / BigQuery with minor date-function adjustments.
