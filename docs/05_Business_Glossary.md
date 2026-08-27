# 05 — Business Glossary

**Version:** 1.0  

---

## Retail & organization terms

| Term | Definition |
|---|---|
| **Corporación Favorita** | Ecuadorian grocery retailer; source of the Kaggle competition dataset |
| **Store** | A physical retail location identified by `store_nbr` (1–54) |
| **Product family** | Product category grouping (33 families, e.g. Grocery I, Beverages, Produce) |
| **Store type** | Format classification: A (large), B (medium), C (small), D (specialty) |
| **Cluster** | Internal store grouping (1–17) used for similar-store analysis |
| **On promotion** | Count of item variants on promotion for that store × family × day (`onpromotion`) |
| **Transaction** | Store-day count of customer transactions (basket proxy, not item-level) |

## Geographic terms

| Term | Definition |
|---|---|
| **City** | Municipality where the store operates (e.g. Quito, Guayaquil, Manta) |
| **State** | Ecuadorian province (e.g. Pichincha, Guayas, Manabí) |
| **National holiday** | Country-wide holiday from `holidays_events.csv` where `locale = National` |
| **Transferred holiday** | Holiday moved to another date; excluded from `is_holiday` flag when `transferred = True` |

## Calendar & economic terms

| Term | Definition |
|---|---|
| **Payday** | 15th or last day of month — Ecuador public-sector wage payment dates; engineered as `is_payday` |
| **Weekend uplift** | Percentage difference in average sales on Saturday/Sunday vs Monday–Friday |
| **Holiday uplift** | Percentage difference in average sales on national holidays vs regular days |
| **Oil price (WTI)** | West Texas Intermediate crude price (`dcoilwtico`); macro indicator for Ecuador's oil-linked economy |
| **YoY growth** | Year-over-year change in total sales: (current year ÷ prior year) − 1 |

## Analytics & modeling terms

| Term | Definition |
|---|---|
| **Grain** | Level of detail in a dataset (e.g. store × family × day) |
| **RMSLE** | Root Mean Squared Logarithmic Error — competition metric; penalizes relative error, suited to mixed-scale sales |
| **Baseline** | Simple forecasting method used for comparison (naive, moving average, same-weekday average) |
| **LightGBM** | Gradient-boosted tree model selected as best performer (RMSLE 0.465) |
| **Hold-out validation** | Last 16 days of training data reserved for model evaluation |
| **Data leakage** | Using information not available at prediction time (e.g. same-day transactions in forecast features) |
| **Feature engineering** | Creating predictive inputs from raw columns (calendar, lifecycle, flags) |
| **Star schema** | BI data model: fact tables (metrics) joined to dimension tables (attributes) |

## KPI terms

| Term | Definition |
|---|---|
| **Total sales** | Sum of `sales` across all rows in the analysis window ($1.07B) |
| **Avg daily sales** | Total sales ÷ distinct days ($637.6K) |
| **Sales per transaction** | Ticket-size proxy: daily store sales ÷ transaction count |
| **Zero-sales row** | Row where `sales = 0` (31.3% of rows — stock-out or no-demand signal) |
| **Category share** | Family's total sales as percentage of chain total |
| **Store sales rank** | Rank by total sales; should be adjusted for `days_since_store_open` |

## Technical / project terms

| Term | Definition |
|---|---|
| **ETL** | Extract, Transform, Load — Python batch pipeline in `etl/` |
| **Phase 0–5** | Sequential pipeline stages from merge through BI export |
| **Parquet** | Columnar file format for processed datasets |
| **DAX** | Data Analysis Expressions — formula language in Power BI measures |

---

## Related documents

- [06_KPI_Definition.md](06_KPI_Definition.md)
- [08_Data_Dictionary.md](08_Data_Dictionary.md)
- [11_Business_Rules.md](11_Business_Rules.md)
