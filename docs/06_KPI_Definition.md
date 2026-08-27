# 06 — KPI Definition

**Version:** 1.0  
**Source data:** `data/processed/cleaned_train.parquet` (2013-01-01 → 2017-08-15)  
**Outputs:** `reports/kpi_report.md`, `reports/kpi_summary.csv`, `data/processed/kpi_*.csv`

---

## 1. KPI catalog

### 1.1 Headline KPIs (executive)

| KPI ID | Name | Formula / logic | Value | Owner | Frequency |
|---|---|---|---|---|---|
| KPI-01 | Total Sales | `SUM(sales)` | $1.07B | Finance / Ops | Monthly |
| KPI-02 | Avg Daily Sales | `SUM(sales) / COUNT(DISTINCT date)` | $637.6K | Ops | Daily / Monthly |
| KPI-03 | YoY Growth 2013→2014 | `(sales_2014 / sales_2013) - 1` | +49.2% | Finance | Annual |
| KPI-04 | YoY Growth 2014→2015 | Same pattern | +15.0% | Finance | Annual |
| KPI-05 | YoY Growth 2015→2016 | Same pattern | +19.8% | Finance | Annual |
| KPI-06 | Weekend Uplift | `AVG(sales \| is_weekend) / AVG(sales \| weekday) - 1` | +39.3% | Ops | Monthly |
| KPI-07 | Holiday Uplift | `AVG(sales \| is_holiday) / AVG(sales \| regular) - 1` | +19.0% | Merchandising | Monthly |
| KPI-08 | Payday Uplift | `AVG(sales \| is_payday) / AVG(sales \| regular) - 1` | +1.4% | Merchandising | Monthly |
| KPI-09 | Oil ↔ Sales Correlation | Pearson(monthly_sales, avg_oil_price) | −0.75 | Finance | Quarterly |
| KPI-10 | Avg Sales per Transaction | `SUM(sales) / SUM(transactions)` on store-days with tx > 0 | $7.46 | Merchandising | Monthly |
| KPI-11 | % Zero-Sales Rows | `COUNT(sales=0) / COUNT(*)` | 31.3% | Supply Chain | Monthly |
| KPI-12 | Forecast RMSLE | RMSLE on 16-day hold-out | 0.465 | Supply Chain | Per model run |

### 1.2 Store-level KPIs

| KPI ID | Name | Formula | Output file |
|---|---|---|---|
| KPI-S01 | Store Total Sales | `SUM(sales) GROUP BY store_nbr` | `kpi_store.csv` |
| KPI-S02 | Store Sales Rank | `RANK(SUM(sales) DESC)` | `kpi_store.csv` |
| KPI-S03 | Store Avg Daily Sales | Total sales ÷ active days | `kpi_store.csv` |
| KPI-S04 | Days Since Store Open | `days_since_store_open` (max/min per store) | `cleaned_train.parquet` |

**Business rule:** KPI-S02 must be interpreted alongside KPI-S04 — store 52 (Manta) ranks last partly due to partial operating history.

### 1.3 Category-level KPIs

| KPI ID | Name | Formula | Output file |
|---|---|---|---|
| KPI-C01 | Category Total Sales | `SUM(sales) GROUP BY family` | `kpi_category.csv` |
| KPI-C02 | Category Revenue Share | Category total / chain total × 100 | `kpi_category.csv` |
| KPI-C03 | Category Rank | Rank by total sales descending | `kpi_category.csv` |
| KPI-C04 | Promo Uplift (correlational) | Avg sales when `onpromotion > 0` vs `= 0` | `kpi_category.csv` |

### 1.4 Monthly KPIs

| KPI ID | Name | Output file |
|---|---|---|
| KPI-M01 | Monthly Total Sales | `kpi_monthly.csv` |
| KPI-M02 | Monthly Avg Oil Price | `kpi_monthly.csv` |
| KPI-M03 | Monthly Holiday Count | `kpi_monthly.csv` |
| KPI-M04 | Monthly YoY Growth % | `kpi_monthly.csv` |

---

## 2. KPI thresholds & targets (recommended)

| KPI | Green | Amber | Red | Action |
|---|---|---|---|---|
| YoY Growth | > +15% | +5% to +15% | < +5% | Review category mix & store expansion |
| Weekend Uplift | 35–45% | 25–35% or > 45% | < 25% | Review staffing calendar |
| Holiday Uplift | 15–25% | 10–15% | < 10% | Review holiday inventory prep |
| % Zero-Sales Rows | < 25% | 25–35% | > 35% | Investigate stock availability |
| Forecast RMSLE | < 0.47 | 0.47–0.52 | > 0.52 | Retrain model / review features |

---

## 3. Power BI DAX measures (dashboard KPIs)

```dax
Total Sales = SUM(fact_sales_actual[sales])
Total Forecast Sales = SUM(fact_sales_forecast[forecast_sales])
Avg Daily Sales = DIVIDE([Total Sales], DISTINCTCOUNT(fact_sales_actual[date]))
Holiday Uplift % = /* not yet defined */
Payday Uplift % = /* not yet defined */
Sales Rank by Store = RANKX(ALL(dim_store[store_nbr]), [Total Sales], , DESC)
```

---

## 4. KPI data lineage

```
train.csv + stores + oil + holidays + transactions
    → merged_train.parquet (phase0)
    → cleaned_train.parquet (phase1)
    → phase3_kpi_reporting.py
        → reports/kpi_report.md
        → reports/kpi_summary.csv
        → data/processed/kpi_store.csv
        → data/processed/kpi_category.csv
        → data/processed/kpi_monthly.csv
    → phase5_powerbi_export.py
        → dashboard/data/fact_sales_actual.parquet
```

---

## 5. Related documents

- [reports/kpi_report.md](../reports/kpi_report.md)
- [02_Business_Requirements.md](02_Business_Requirements.md)
- [17_Dashboard_Design.md](17_Dashboard_Design.md)
