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

## Procurement layer (`data/processed/`, phase 7 — fully simulated)

| Table | Role | Format |
|---|---|---|
| `fact_purchase_order_sim` | PO lines: order/receipt dates, quantities, prices, PPV, service flags | Parquet |
| `dim_supplier_sim` | Supplier master: lead time, reliability, price factor | CSV |
| `dim_family_sourcing_sim` | Primary and secondary supplier per family | CSV |

## Inventory layer (`data/processed/`, phase 8 — derived from phase-7 receipts)

| Table | Role | Format |
|---|---|---|
| `fact_inventory_sim` | Daily opening/closing stock, fulfilled and unfulfilled units, inventory value | Parquet |
| `kpi_inventory_sim` | Merchandising KPIs per family | CSV |
| `kpi_inventory_store_sim` | Merchandising KPIs per store | CSV |

## Pricing layer (`data/processed/`, phase 9 — derived)

| Table | Role | Format |
|---|---|---|
| `kpi_pricing_sim` | Revenue (fulfilled basis), markdown, margin per family | CSV |
| `kpi_pricing_store_sim` | The same per store, plus basket-adjusted price position | CSV |
| `kpi_margin_bridge_sim` | YoY margin change split into volume, price and cost effects | CSV |

## Price sensitivity layer (`data/processed/`, phase 10 — derived)

| Table | Role | Format |
|---|---|---|
| `kpi_break_even_elasticity_sim` | Volume needed to hold margin at each price step, per family | CSV |
| `kpi_price_scenario_sim` | Price grid × explicit elasticity assumptions → revenue and margin change | CSV |
| `diagnostic_price_volume_regression_sim` | **Not a KPI.** Methodological guardrail showing why a regression on simulated prices is not elasticity evidence | CSV |

Design and limits: [23_Price_Sensitivity_Design.md](23_Price_Sensitivity_Design.md).

Revenue basis and definitions: [22_Pricing_Profitability.md](22_Pricing_Profitability.md).

Equation, audit and KPI definitions: [21_Inventory_Simulation.md](21_Inventory_Simulation.md).

Rules and provenance: [20_Procurement_Simulation.md](20_Procurement_Simulation.md).

Rules and provenance: [19_Simulation_Design.md](19_Simulation_Design.md).
