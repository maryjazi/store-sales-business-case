# Business Case: Sales Analytics & Demand Forecasting for a Multi-Store Retail Chain

**Prepared for:** Retail Operations & Merchandising Leadership
**Data source:** [Kaggle – Store Sales Time Series Forecasting](https://www.kaggle.com/competitions/store-sales-time-series-forecasting) (Corporación Favorita, Ecuador)
**Period analyzed:** January 1, 2013 – August 15, 2017

---

## 1. Executive Summary

This project analyzes 4.7 years of daily sales across 54 stores and 33 product categories ($1.07B in total recorded sales) to answer three business questions: what drives sales, how predictable is demand, and what should the business do differently.

Three findings stand out. First, growth has been strong but decelerating — sales roughly doubled from 2013 to 2016, but year-over-year growth slowed from +49% (2013→2014) to +15–20% in subsequent years, suggesting the business is maturing past its early expansion phase. Second, sales are highly concentrated: three categories (Grocery I, Beverages, Produce) generate 64% of all revenue, and the top 5 of 54 stores — all in Quito — outsell the bottom 5 by roughly 8x. Third, a machine-learning forecasting model beats naive planning methods by a meaningful margin (11% lower error than the best simple baseline), which translates directly into better inventory and staffing decisions.

The recommendations in Section 8 focus on three levers: protecting and growing the concentrated core categories, addressing underperformance at specific stores (correcting for store-lifecycle effects rather than misreading them as failure), and formalizing a demand-forecasting process using the model built here.

## 2. Business Problem

Retail chains lose money two ways when demand is mispredicted: overstocking ties up capital and increases waste/markdowns, while understocking loses sales and damages customer trust. Both risks compound across a chain with dozens of stores and dozens of categories, where demand is shaped by store-specific factors (location, format, tenure), calendar effects (holidays, paydays, weekends), and external conditions (regional economic indicators like oil price, in an oil-dependent economy like Ecuador's).

This project builds the analytical foundation to manage that uncertainty: a clean, feature-rich dataset; a defined set of KPIs leadership can track on a recurring basis; a forecasting model benchmarked against realistic alternatives; and a dashboard for ongoing monitoring.

## 3. Objectives

- Quantify historical sales patterns by store, category, and region
- Measure the impact of holidays, paydays, promotions, and oil prices on demand
- Build and validate a demand forecasting model against honest baselines
- Define a KPI set for recurring business reporting
- Deliver a Power BI dashboard for self-service monitoring

## 4. Data & Methodology

**Data.** Six source tables were merged into a single analytical dataset: daily sales by store and category, store metadata (city, state, format type, cluster), national holiday calendar, daily oil price, and store-level transaction counts.

**Cleaning decisions (fully documented in `README.md` and `etl/`):**
- Missing transaction counts (245,784 rows, 98.7% of which had zero sales) were filled with 0 rather than dropped, preserving every store-day in the dataset.
- A data-quality issue was caught and fixed: some calendar dates had duplicate holiday records, which silently inflated row counts on a naive merge (3,000,888 → 3,008,016 rows) — resolved by deduplicating holidays per date before merging.
- Extreme sales values (top 0.1% per category) were flagged, not removed — they represent real demand spikes (e.g., holiday shopping), not data errors.
- A `days_since_store_open` feature was engineered after discovering several stores (e.g., store 52) began operating partway through the data window — without it, a "new store" and an "underperforming store" look identical to a model or a manager.

**Validation design.** Because the competition's true test labels are private, the last 16 days of the training data were held out as a validation set — matching the actual forecast horizon — with the model trained only on data before that window. This avoids information leakage and gives an honest accuracy estimate.

## 5. Key Findings

**Growth is real but slowing.** Total sales grew ~49% in 2014, then ~15% and ~20% in the following two years — still healthy, but a different growth profile than the business's early years, relevant for setting realistic forward targets.

**Revenue is concentrated in a few categories.** Grocery I (32% of total sales), Beverages (20%), and Produce (11%) together account for 64% of revenue. This is a normal pattern for a grocery-format retailer, but it also means supply disruptions or stockouts in these three categories have an outsized impact on total revenue.

**Store performance varies by nearly 10x, but "worst" isn't always "worst."** The top 5 stores (all in Quito) each generate $43–62M over the period; the bottom 5 generate $2.7–7.7M. The lowest-ranked store (52, Manta) is a partial exception — it opened partway through the data window, so its low *total* is partly a tenure artifact rather than pure underperformance. Store rankings used for performance management should control for this.

**Calendar effects are large and actionable.** Weekend sales run 39% above weekday sales on average; national holidays add a further 19% uplift. Payday (the 15th and month-end, when Ecuador's public sector disburses wages) shows only a modest 1.4% uplift at the whole-basket level — smaller than expected, and worth re-testing at the category level in future work, since payday effects are more likely concentrated in specific categories than spread evenly.

**Oil price moves inversely with sales.** Monthly sales and average oil price show a strong negative correlation (r ≈ −0.75) over the period. In an oil-linked economy, this is a plausible macro relationship, not a store-level lever — it's useful for macro planning assumptions, not for day-to-day store decisions.

**Promotions correlate with much higher sales, but the effect size needs a caveat.** Promoted rows show ~619% higher average sales than non-promoted rows. This is inflated by category mix — categories like School & Office Supplies show extreme uplift mainly because they barely sell outside promo periods (back-to-school season), not because promotion alone multiplies sales 40x. A causal, category-controlled estimate is a natural next step (Section 9).

## 6. KPI Framework

The following KPIs (full detail in `reports/kpi_report.md` and `data/processed/kpi_*.csv`) are recommended for recurring reporting:

| KPI | Value (period) | Business Use |
|---|---|---|
| Total Sales | $1.07B | Headline revenue tracking |
| Avg Daily Sales | $637.6K | Daily operating baseline |
| YoY Growth | +49.2% / +15.0% / +19.8% (2014/2015/2016) | Growth trend, target-setting |
| Weekend Uplift | +39.3% | Staffing/inventory planning |
| Holiday Uplift | +19.0% | Promotional & staffing calendar |
| Avg Sales per Transaction | $7.46 | Basket-size proxy, pricing/upsell signal |
| % Zero-Sales Rows | 31.3% | Stock availability / demand-coverage signal |
| Store Sales Rank | See `kpi_store.csv` | Performance management (adjust for store tenure) |

## 7. Forecasting Model & Results

Four approaches were compared on the held-out 16-day validation window, scored with RMSLE (the metric this Kaggle competition itself uses — it penalizes relative, not absolute, error, which suits a business with both $10 and $10,000/day product lines):

| Model | RMSLE (lower = better) |
|---|---|
| Naive last-value | 0.660 |
| Same-weekday average (last 4 weeks) | 0.531 |
| 28-day moving average | 0.522 |
| **LightGBM (engineered features)** | **0.465** |

The gradient-boosted model outperforms the strongest simple baseline by ~11%, using store identity, product category, store tenure (`days_since_store_open`), day-of-year seasonality, and promotion status as its top five predictive features. The model was trained on a 900,000-row sample for compute-budget reasons in this environment (2 CPU cores); retraining on the full ~2.97M-row training set on standard hardware would likely improve this further.

**External validation.** The forecast was submitted to Kaggle's live leaderboard and scored **RMSLE 0.48464** on Kaggle's own held-out test set — close to the internal validation estimate (0.465), which confirms the validation methodology (a realistic, leakage-free time-based split) generalizes well to genuinely unseen data rather than being an artifact of how the validation set was chosen.

The trained model was used to generate a 16-day forward forecast for the actual competition test window (Aug 16–31, 2017), available at `reports/forecast_submission.csv` and in dashboard-ready form at `data/processed/forecast_detail.parquet`.

## 8. Business Recommendations

**Protect the core, but watch concentration risk.** With 64% of revenue in three categories, even short supply disruptions there have an outsized revenue impact. Recommend a tighter stock-availability SLA specifically for Grocery I, Beverages, and Produce, monitored via the "% Zero-Sales Rows" KPI at the category level.

**Re-baseline store performance for tenure.** Before using total-sales rankings for store-level performance conversations, adjust for `days_since_store_open` — comparing a store open 8 months to one open 4 years on raw totals will misattribute a ramp-up curve as underperformance.

**Move from flat to seasonally-aware staffing and promotion calendars.** The measured 39% weekend and 19% holiday uplifts are large enough to justify formal staffing/inventory rules tied to the calendar, rather than manual adjustment.

**Adopt the forecasting model for replenishment planning, with a monitoring plan.** An 11% accuracy improvement over the best simple baseline is meaningful at scale, but should be rolled out with a monitoring KPI (rolling RMSLE) so degradation is caught early, and revisited quarterly as more data accumulates.

**Investigate promotion ROI per category before expanding promo spend.** The headline +619% promotion uplift is not a safe planning number as-is; recommend a controlled, category-level analysis (Section 9) before using it to justify incremental promotional budget.

## 9. Limitations & Next Steps

- The forecasting model was trained on a data sample due to this environment's compute constraints; full-data retraining is a low-effort next step with likely accuracy gains.
- Promotion effect estimates are correlational, not causal; a category-controlled or matched analysis would give a more trustworthy ROI figure.
- The payday effect was measured at the whole-basket level and came out smaller than expected; a category-level breakdown may reveal concentrated effects (e.g., in higher-ticket categories) masked by the aggregate.
- Regional/store-cluster segmentation (beyond city-level) was not explored in depth and is a natural extension for targeted, store-cluster-specific recommendations.

## Appendix: Supporting Files

- Figures: `reports/figures/01`–`12` (trend, seasonality, category/region, holiday/payday/oil effects, model validation, feature importance, model comparison)
- Full KPI tables: `reports/kpi_summary.csv`, `data/processed/kpi_store.csv`, `kpi_category.csv`, `kpi_monthly.csv`
- Model artifacts: `data/processed/lightgbm_model.txt`, `reports/model_comparison.json`, `reports/feature_importance.csv`
- Forecast output: `reports/forecast_submission.csv`, `data/processed/forecast_detail.parquet`
- Power BI data model: `dashboard/data/` (build guide: `docs/17_Dashboard_Design.md`)
