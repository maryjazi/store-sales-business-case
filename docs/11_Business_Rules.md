# 11 — Business Rules

**Version:** 1.0  

---

## 1. Data merge rules

| Rule ID | Rule | Rationale | Implementation |
|---|---|---|---|
| BR-M01 | Join stores to train with **left join** on `store_nbr` | Preserve all sales rows | phase0 |
| BR-M02 | Oil price gaps filled **forward-fill then backward-fill** | oil.csv has weekday-only entries | phase0 |
| BR-M03 | Only **National** holidays used in phase 0 | Avoid locale mismatch complexity | phase0 |
| BR-M04 | Exclude holidays where `transferred = True` | Transferred dates are not the actual holiday | phase0 |
| BR-M05 | **Deduplicate holidays by date** (keep first) | Prevents row inflation (3,008,016 → 3,000,888) | phase0 |
| BR-M06 | Join transactions with **left join** | Preserve all sales rows even without tx data | phase0 |

---

## 2. Data cleaning rules

| Rule ID | Rule | Rationale | Implementation |
|---|---|---|---|
| BR-C01 | Missing `transactions` → fill with **0** | 98.7% of missing tx rows also have sales=0 | phase1 |
| BR-C02 | Set `transactions_missing = True` when originally null | Audit trail for data quality | phase1 |
| BR-C03 | Do **not drop** zero-sales rows | Valid business state (no demand / stock-out) | phase1 |
| BR-C04 | Flag outliers at **99.9th percentile within family** | Real demand spikes, not errors | phase1 |
| BR-C05 | Do **not remove** flagged outliers | Holiday spikes are real | phase1 |
| BR-C06 | Exclude `transactions` from **forecast feature set** | Same-day metric unknown at prediction time | phase1 |

---

## 3. Feature engineering rules

| Rule ID | Rule | Rationale | Implementation |
|---|---|---|---|
| BR-F01 | `is_payday` = day is **15th OR last day of month** | Ecuador public-sector wage cycle | features.py |
| BR-F02 | `is_weekend` = Saturday or Sunday | Standard retail calendar | features.py |
| BR-F03 | Store open date = **first date with sales > 0** per store | Proxy for operating start | features.py |
| BR-F04 | `days_since_store_open` clipped to **≥ 0** | Prevent negative tenure | features.py |
| BR-F05 | Apply **identical transforms** to train and test | Prevent train/test skew | features.py |

---

## 4. KPI calculation rules

| Rule ID | Rule | Rationale | Implementation |
|---|---|---|---|
| BR-K01 | YoY growth excludes **2017** (partial year) | Avoid misleading partial-year comparison | phase3 |
| BR-K02 | Weekend uplift = avg row sales weekend vs weekday | Simple day-level comparison | phase3 |
| BR-K03 | Holiday uplift uses `is_holiday` flag | National holidays only | phase3 |
| BR-K04 | Store ranking by **total sales** with lifecycle caveat | Document store 52 artifact | phase3, business case |
| BR-K05 | Category share = family total / chain total × 100 | Standard concentration metric | phase3 |
| BR-K06 | Promo uplift is **correlational**, not causal | Category mix confounds raw comparison | phase3, kpi_report |

---

## 5. Forecasting rules

| Rule ID | Rule | Rationale | Implementation |
|---|---|---|---|
| BR-FC01 | Validation window = **last 16 days** of train | Matches test horizon | phase4 |
| BR-FC02 | Train only on data **before** validation window | Prevent leakage | phase4 |
| BR-FC03 | Primary metric = **RMSLE** | Competition standard; handles scale mix | phase4 |
| BR-FC04 | Compare against **≥ 3 baselines** before selecting ML | Prove ML adds value | phase4 |
| BR-FC05 | Predictions clipped to **≥ 0** | Sales cannot be negative | phase4b |
| BR-FC06 | Model selection = **lowest validation RMSLE** | LightGBM selected (0.465) | phase4 |

---

## 6. Reporting & dashboard rules

| Rule ID | Rule | Rationale | Implementation |
|---|---|---|---|
| BR-R01 | Executive KPIs rounded to **1 decimal** for percentages | Readability | kpi_report |
| BR-R02 | All sales figures are **unit quantities**, not currency (the dataset has no price column) | Prevents unsupported revenue claims | All reports |
| BR-R03 | Dashboard uses **star schema** (not flat table) | BI best practice | phase5 |
| BR-R04 | Actual and forecast share **same dimensions** | Consistent drill-down | phase5 |
| BR-R05 | Store performance conversations must consider **store tenure** | Fair comparison | business case §8 |

---

## 7. Rule change log

| Date | Rule | Change | Approved by |
|---|---|---|---|
| Phase 0 | BR-M05 | Added holiday dedup after row-count anomaly discovered | Data Analyst |
| Phase 1 | BR-C06 | Excluded transactions from forecast features | Supply Chain (interview) |
| Phase 3 | BR-K06 | Added correlational caveat on promo uplift | Merchandising (interview) |

---

## 8. Related documents

- [05_Business_Glossary.md](05_Business_Glossary.md)
- [06_KPI_Definition.md](06_KPI_Definition.md)
- [12_Assumptions_Constraints.md](12_Assumptions_Constraints.md)
