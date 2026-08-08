# Portfolio Summary

Ready-to-use text for a resume, LinkedIn profile, or cover letter. Fill in the bracketed links once the repo is pushed to GitHub and the Power BI screenshots are added.

## Resume Bullets

Pick 2–4 depending on the role (data analyst vs. data scientist vs. BI-focused). For **Data Analyst / BI Analyst / Reporting Analyst** roles (e.g. in Germany), lead with the first bullet — it's the one-line summary of the whole project and matches what those job postings screen for (end-to-end workflow, data quality, dimensional modeling, KPI design, stakeholder-ready reporting):

- Designed an end-to-end analytical workflow from raw CSV files to an interactive Power BI dashboard, applying data quality checks, dimensional modeling (star schema), KPI design, and demand forecasting for business decision support.
- Built an end-to-end sales analytics and forecasting pipeline on 3M+ retail transaction records (54 stores, 33 categories, 4.7 years) using Python (pandas), covering data cleaning, feature engineering, and exploratory analysis.
- Designed and validated a LightGBM demand-forecasting model, beating the strongest baseline (moving average) by 11% (RMSLE 0.465 vs 0.522) using a leakage-free, time-based validation split — confirmed with a real Kaggle leaderboard submission scoring RMSLE 0.48464.
- Defined and reported a business KPI framework (revenue growth, category concentration, holiday/weekend uplift, store performance) translating raw transaction data into decision-ready metrics for retail operations.
- Designed a Power BI star schema (fact/dimension model) and interactive dashboard with DAX measures for sales trend, category, regional, and store-performance reporting.
- Authored a business case report with quantified findings and actionable recommendations for retail leadership, including a documented data-quality fix that prevented a ~7,000-row merge error.

## LinkedIn / Portfolio Blurb

> Built a full sales analytics & forecasting project on a 3M-row multi-store retail dataset (Kaggle's Corporación Favorita competition): data cleaning and feature engineering in Python, exploratory analysis of sales drivers (seasonality, holidays, promotions, oil price), a LightGBM forecasting model validated against three baselines (11% error reduction), a business KPI framework, and an interactive Power BI dashboard — all documented end-to-end in a public GitHub repo with a written business case and recommendations.
> 🔗 [GitHub repo link] · [Dashboard screenshot / demo]

## One-Line Version (for a resume header/summary)

> Sales analytics & forecasting project (Python, LightGBM, Power BI) on 3M-row retail dataset — 11% forecast accuracy improvement over baseline, verified with a live Kaggle leaderboard score (RMSLE 0.48464), full KPI framework and business case.

## Talking Points for Interviews

- **Why LightGBM over ARIMA/Prophet?** With 1,782 individual (store × family) series, per-series statistical models don't scale well; a single tabular ML model using store/category/date features as predictors handles all series jointly and captures cross-series patterns (e.g. shared calendar effects) that isolated time-series models would miss.
- **How did you validate without leaking the future?** Held out the last 16 days of training data (matching the real forecast horizon) and trained only on prior data — mirrors how the model would actually be used in production.
- **What was the trickiest data issue?** A silent row-count inflation from duplicate holiday records on certain dates (caught by comparing merged row count to the pre-merge row count) — a reminder to always sanity-check row counts after every join.
- **What would you do with more time/compute?** Retrain on the full 2.97M-row training set (sampled to 900k here for a 2-core environment), add a category-controlled promotion-ROI analysis, and test store-cluster-specific models.
- **How do you know your validation wasn't optimistic?** Submitted the forecast to Kaggle's actual leaderboard — RMSLE 0.48464, close to the 0.465 from internal validation. A large gap would have signaled overfitting to the validation window; the close match is evidence the time-based split was a fair test.
