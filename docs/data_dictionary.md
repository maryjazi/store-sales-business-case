# Data Dictionary

## Raw sources (`data/raw/`)

| File | Grain | Key columns |
|---|---|---|
| `train.csv` | store × family × day | `id`, `date`, `store_nbr`, `family`, `sales`, `onpromotion` |
| `test.csv` | store × family × day | `id`, `date`, `store_nbr`, `family`, `onpromotion` |
| `stores.csv` | store | `store_nbr`, `city`, `state`, `type`, `cluster` |
| `oil.csv` | day | `date`, `dcoilwtico` |
| `holidays_events.csv` | event | `date`, `type`, `locale`, `locale_name`, `description`, `transferred` |
| `transactions.csv` | store × day | `date`, `store_nbr`, `transactions` |

## Processed datasets (`data/processed/`)

| File | Produced by | Description |
|---|---|---|
| `merged_train.parquet` | phase0 | Raw train joined with stores, oil, transactions, holidays |
| `cleaned_train.parquet` | phase1 | Feature-engineered training set (~30 columns) |
| `prepared_test.parquet` | phase1 | Feature-engineered test set (no `sales`, no `transactions`) |
| `lightgbm_model.txt` | phase4 | Saved LightGBM booster |
| `val_predictions.parquet` | phase4 | Hold-out validation predictions |
| `forecast_detail.parquet` | phase4b | Test-window forecasts with date/store/family |
| `kpi_store.csv` | phase3 | Per-store KPI rollup |
| `kpi_category.csv` | phase3 | Per-family KPI rollup |
| `kpi_monthly.csv` | phase3 | Monthly sales trend |

### Key engineered features (phase1)

| Column | Type | Definition |
|---|---|---|
| `is_payday` | bool | Day is 15th or last day of month (Ecuador wage cycle) |
| `is_weekend` | bool | Saturday or Sunday |
| `days_since_store_open` | int | Days since store's first day with sales > 0 |
| `transactions_missing` | bool | Original row had no transaction record |
| `sales_outlier_flag` | bool | Sales above 99.9th percentile within family |
| `is_holiday` | bool | National non-transferred holiday on that date |

## Dashboard star schema (`dashboard/data/`)

| Table | Role | Format |
|---|---|---|
| `fact_sales_actual` | Daily actual sales | Parquet |
| `fact_sales_forecast` | Daily forecast sales | Parquet |
| `dim_store` | Store attributes | CSV |
| `dim_date` | Calendar attributes | CSV |
| `dim_family` | Product family + `family_group` | CSV |

## Commercial layer (`data/processed/`, phase 6 — simulated)

| Table | Role | Format |
|---|---|---|
| `fact_sales_commercial` | Real units + simulated price, cost, revenue, margin (`_sim` columns) | Parquet |
| `dim_product_cost` | Base price and cost ratio per family | CSV |
| `dim_store_price_index` | Store-level price index | CSV |

Rules and provenance: [19_Simulation_Design.md](19_Simulation_Design.md).
