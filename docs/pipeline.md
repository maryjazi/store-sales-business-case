# Pipeline Runbook

Run all phases from the repository root after placing Kaggle CSVs in `data/raw/`.

```bash
pip install -r requirements.txt

python etl/phase0_data_understanding.py
python etl/phase1_cleaning_features.py
python etl/phase2_eda.py
python etl/phase3_kpi_reporting.py
python etl/phase4_forecasting.py
python etl/phase4b_generate_forecast.py
python etl/phase5_powerbi_export.py
python etl/phase6_simulation_layer.py
python etl/phase7_procurement.py
python etl/phase8_inventory.py
python etl/phase9_pricing.py
```

## Phase map

| Phase | Script | Primary outputs |
|---|---|---|
| 0 | `phase0_data_understanding.py` | `data/processed/merged_train.parquet` |
| 1 | `phase1_cleaning_features.py` | `cleaned_train.parquet`, `prepared_test.parquet` |
| 2 | `phase2_eda.py` | `reports/figures/01–09`, `reports/eda_insights.json` |
| 3 | `phase3_kpi_reporting.py` | `reports/kpi_report.md`, `reports/kpi_summary.csv`, KPI CSVs |
| 4 | `phase4_forecasting.py` | `lightgbm_model.txt`, `reports/figures/10–12`, model metrics |
| 4b | `phase4b_generate_forecast.py` | `reports/forecast_submission.csv`, `forecast_detail.parquet` |
| 5 | `phase5_powerbi_export.py` | `dashboard/data/*` star schema |
| 6 | `phase6_simulation_layer.py` | `fact_sales_commercial.parquet`, `dim_product_cost.csv`, `dim_store_price_index.csv` |
| 7 | `phase7_procurement.py` | `fact_purchase_order_sim.parquet`, `dim_supplier_sim.csv`, `dim_family_sourcing_sim.csv` |
| 8 | `phase8_inventory.py` | `fact_inventory_sim.parquet`, `kpi_inventory_sim.csv`, `kpi_inventory_store_sim.csv` |
| 9 | `phase9_pricing.py` | `kpi_pricing_sim.csv`, `kpi_pricing_store_sim.csv`, `kpi_margin_bridge_sim.csv`, `reports/pricing_profitability_sim.md` |

## Validation checkpoints

After each phase, confirm the expected artifact exists and row counts match README Data Notes:

- Phase 0: merged shape **3,000,888 × 15**
- Phase 1: cleaned shape **3,000,888 × 30**; prepared test **28,512 rows**
- Phase 4: validation RMSLE ≈ **0.465** (LightGBM)
- Phase 6: commercial layer **3,000,888 rows**, chain gross margin ≈ **22.6%** (test-enforced band: 20–28%)
- Phase 7: **294,535 PO lines**, on-time delivery ≈ **86.5%** (test-enforced band: 80–92%)
- Phase 8: inventory equation reconciles exactly (the script aborts otherwise); simulated demand fulfillment rate ≈ **98.5%** (test-enforced band: 95–100%)
- Phase 9: revenue views reconcile and the margin bridge closes (the script aborts otherwise); chain gross margin ≈ **22.6%** (test-enforced band: 20–28%)

## SQL alternative

Analytical queries equivalent to phases 0 and 3 are in `sql/`. Load raw CSVs into your warehouse (BigQuery, Snowflake, PostgreSQL) and run the scripts there for ad-hoc exploration without Python.
