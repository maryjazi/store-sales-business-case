# 13 — Risk Assessment

**Version:** 1.0  
**Review date:** August 2026  

---

## 1. Risk register

| ID | Risk | Category | Likelihood | Impact | Score | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|---|---|
| R-01 | Row-count inflation from bad joins | Data quality | Medium | High | **High** | Dedup holidays; assert row count; automated tests | Data Analyst | ✅ Mitigated |
| R-02 | Data leakage in forecast model | Modeling | Medium | High | **High** | Exclude transactions; time-based hold-out | Data Analyst | ✅ Mitigated |
| R-03 | Overfitting to validation window | Modeling | Medium | Medium | **Medium** | Kaggle external validation (0.48464) | Data Analyst | ✅ Mitigated |
| R-04 | Model trained on sample, not full data | Modeling | High | Medium | **Medium** | Document retrain recommendation | Data Analyst | 🟡 Open |
| R-05 | Promotion ROI misinterpreted as causal | Business | High | High | **High** | Caveats in KPI report & business case | Merchandising | 🟡 Monitored |
| R-06 | Unfair store ranking penalizes new stores | Business | Medium | Medium | **Medium** | `days_since_store_open` feature + business rule | Ops | ✅ Mitigated |
| R-07 | Raw data unavailable (Kaggle downtime) | External | Low | High | **Medium** | Processed outputs in repo; download docs | Data Analyst | ✅ Mitigated |
| R-08 | Forecast degrades over time (concept drift) | Modeling | Medium | High | **High** | Recommend rolling RMSLE monitoring | Supply Chain | 🟡 Open |
| R-09 | Oil correlation treated as causal | Business | Medium | Medium | **Medium** | Document as macro signal only | Finance | ✅ Mitigated |
| R-10 | Compute timeout on full ETL in CI | Technical | Medium | Low | **Low** | CI runs tests only; ETL manual/scheduled | DevOps | ✅ Mitigated |
| R-11 | Power BI not built / screenshots missing | Delivery | Medium | Low | **Low** | Guide + data ready; Streamlit dashboard now gives a working, tested interactive view of the same KPIs as a fallback | Data Analyst | 🟡 Mitigated by Streamlit; Power BI .pbix still pending |
| R-12 | Category concentration — supply disruption | Business | Low | High | **Medium** | Recommend SLA for top 3 categories | Merchandising | 🟡 Recommended |

**Scoring:** Likelihood × Impact → High / Medium / Low

---

## 2. Risk detail — top 3

### R-01 — Join row inflation (resolved)

**Scenario:** Merging holidays without deduplication silently added ~7,000 rows.  
**Detection:** Compare merged row count to source train count.  
**Resolution:** `drop_duplicates(subset="date")` on national holidays before merge.  
**Verification:** `tests/test_data_quality.py::test_merged_row_count`

### R-02 — Forecast leakage (resolved)

**Scenario:** Including same-day `transactions` as a feature would inflate accuracy unrealistically.  
**Resolution:** Excluded from `prepared_test.parquet` and model feature list.  
**Verification:** Feature importance shows no transaction column.

### R-05 — Promotion misinterpretation (ongoing)

**Scenario:** Merchandising uses +619% headline promo uplift for budget planning.  
**Impact:** Over-investment in promotions with inflated expected return.  
**Mitigation:** Document correlational caveat; recommend category-controlled analysis as next phase.

---

## 3. Residual risks (accepted)

| Risk | Acceptance rationale |
|---|---|
| R-04 Sample training | Portfolio/compute constraint; documented with retrain path |
| R-08 Concept drift | Requires production monitoring infrastructure (out of v1 scope) |
| R-12 Concentration | Business risk acknowledged; recommendation delivered in business case |

---

## 4. Risk response strategies

| Strategy | Risks |
|---|---|
| **Avoid** | R-02 (leakage) — exclude unsafe features |
| **Mitigate** | R-01, R-03, R-06 — tests, validation, lifecycle feature |
| **Transfer** | R-07 — Kaggle hosts data |
| **Accept** | R-04, R-08 — documented with next steps |

---

## 5. Monitoring plan (recommended post go-live)

| Metric | Frequency | Alert threshold |
|---|---|---|
| Rolling forecast RMSLE | Weekly | > 0.52 |
| % zero-sales rows (top 3 categories) | Monthly | > 35% |
| Pipeline row counts | Every ETL run | ≠ 3,000,888 |
| YoY growth | Quarterly | < +5% |

---

## 6. Related documents

- [12_Assumptions_Constraints.md](12_Assumptions_Constraints.md)
- [11_Business_Rules.md](11_Business_Rules.md)
- [reports/business_case.md](../reports/business_case.md) §9 Limitations
