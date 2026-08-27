# 17 — Dashboard Design

**Version:** 1.0  
**Tool:** Power BI Desktop  
**Data source:** `dashboard/data/` (exported by `etl/phase5_powerbi_export.py`)  
**Build guide:** [dashboard/POWERBI_GUIDE.md](../dashboard/POWERBI_GUIDE.md)

---

## 1. Design goals

| Goal | How achieved |
|---|---|
| Self-service KPI monitoring | KPI cards + slicers on every page |
| Actual vs forecast visibility | Combined line chart on Overview |
| Store fairness | Ranking table with city/type context |
| Category concentration | Top-N bar chart + family_group treemap |
| External factor awareness | Holiday/payday uplift cards |

---

## 2. Data model (import)

| Table | Format | Import method |
|---|---|---|
| fact_sales_actual | Parquet | Get Data → Parquet |
| fact_sales_forecast | Parquet | Get Data → Parquet |
| dim_store | CSV | Get Data → Text/CSV |
| dim_date | CSV | Get Data → Text/CSV |
| dim_family | CSV | Get Data → Text/CSV |

**Storage mode:** Import (recommended for portfolio/local use)

---

## 3. DAX measures

| Measure | Purpose |
|---|---|
| `Total Sales` | Sum of actual sales |
| `Total Forecast Sales` | Sum of forecast sales |
| `Avg Daily Sales` | Total sales ÷ distinct days |
| `YoY Sales Growth %` | Year-over-year change |
| `Holiday Uplift %` | Holiday vs regular day avg |
| `Payday Uplift %` | Payday vs regular day avg |
| `Sales Rank by Store` | Rank stores by total sales |

Full DAX definitions: `dashboard/POWERBI_GUIDE.md` § DAX Measures

---

## 4. Page layout

### Page 1 — Overview

| Visual | Fields | Purpose |
|---|---|---|
| Card × 4 | Total Sales, Avg Daily Sales, YoY Growth %, Total Forecast Sales | Headline KPIs |
| Line chart | dim_date[date] × Total Sales + Total Forecast Sales | Trend + forecast |
| Donut / bar | dim_family[family_group] × Total Sales | Category mix |

**Screenshot:** `dashboard/screenshots/overview.png`

---

### Page 2 — Category & Region

| Visual | Fields | Purpose |
|---|---|---|
| Horizontal bar | dim_family[family] × Total Sales (Top 15) | Category ranking |
| Treemap | dim_family[family_group] × Total Sales | Grouped view |
| Bar / Map | dim_store[city] × Total Sales | Geographic breakdown |

---

### Page 3 — Store Performance

| Visual | Fields | Purpose |
|---|---|---|
| Table | store_nbr, city, type, Total Sales, Sales Rank | Manager view |
| Bar chart | dim_store[type] × Total Sales | Format comparison |

**Screenshot:** `dashboard/screenshots/store_analysis.png`

---

### Page 4 — External Factors

| Visual | Fields | Purpose |
|---|---|---|
| Card × 2 | Holiday Uplift %, Payday Uplift % | Calendar effects |
| Bar chart | dim_date[day_name] × Avg sales | Weekly pattern |

---

### Page 5 — Forecast (planned)

| Visual | Fields | Purpose |
|---|---|---|
| Line chart | date × actual vs forecast (last 16 days + forward) | Model output review |
| Table | store, family, forecast_sales | Detail export |

---

## 5. Slicers (global)

| Slicer | Field | Pages |
|---|---|---|
| Year | dim_date[year] | All |
| Date range | dim_date[date] | Overview, Forecast |
| Category group | dim_family[family_group] | All |
| City | dim_store[city] | Store, Category |
| Store type | dim_store[type] | Store |

---

## 6. Color & formatting guidelines

| Element | Recommendation |
|---|---|
| Actual sales line | Solid, primary color (blue) |
| Forecast line | Dashed, secondary color (orange) |
| KPI cards | Large font; conditional color for YoY (green/red) |
| Top stores | Highlight Quito cluster |
| Font | Segoe UI (Power BI default) |

---

## 7. Refresh strategy

| Environment | Refresh method |
|---|---|
| Portfolio / local | Re-run `etl/phase5_powerbi_export.py` → Refresh in Power BI Desktop |
| Production (future) | Scheduled pipeline → cloud data source → automatic refresh |

---

## 8. Acceptance criteria

| Criterion | Status |
|---|---|
| All 5 tables imported with correct relationships | ✅ Data ready |
| Overview page with KPI cards + trend | ✅ Screenshot captured |
| Store Analysis page | ✅ Screenshot captured |
| External Factors page | 🟡 Pending screenshot |
| Forecast page | 🟡 Pending screenshot |
| Slicers functional across pages | 🟡 Verify in Desktop |

---

## 9. Streamlit dashboard (built, testable alternative)

**Tool:** Streamlit + Plotly
**Source:** `dashboard/app.py`
**Data source:** same pre-aggregated tables as the Power BI model above (`reports/`, `data/processed/`) — no separate export step needed

Built as a lightweight companion to the Power BI design in sections 1–8: no desktop app or `.pbix` file required, starts in seconds, and is easy to demo on any machine with Python installed.

### 9.1 What it shows

| Section | Content |
|---|---|
| KPI cards x4 | Total sales, best model RMSLE (with % improvement vs. best baseline), weekend uplift, holiday uplift |
| Monthly sales trend | Line chart, `kpi_monthly.csv` |
| Model comparison | Horizontal bar, all baselines + LightGBM (RMSLE, lower = better) |
| Actual vs. forecast | 16-day validation window, `val_predictions.parquet` |
| Store ranking | Top-10 by sales, filterable by store type (A-E) |
| Category share | Top 8 categories + "Other", `kpi_category.csv` |
| Feature importance | Expander, top 10 LightGBM features |

### 9.2 Run

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```

Opens at `http://localhost:8501`.

### 9.3 Status

Verified headless with `streamlit.testing.v1.AppTest`: loads with zero exceptions, all 4 KPI cards compute correctly, all 6 charts render, and the store-type filter works. This is the dashboard to show live in a demo where Power BI Desktop isn't available or the `.pbix` file isn't on hand.

### 9.4 Relationship to the Power BI design (sections 1-8)

The Power BI design above remains the target BI deliverable (richer slicers, DAX measures, native drill-through). Streamlit is not a replacement for that design — it is a Python-native, zero-install way to demo the same KPIs while the Power BI build is completed.

---

## 10. Related documents

- [06_KPI_Definition.md](06_KPI_Definition.md)
- [16_Data_Model.md](16_Data_Model.md)
- [14_Use_Cases.md](14_Use_Cases.md)
