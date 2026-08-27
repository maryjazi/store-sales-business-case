# 12 — Assumptions & Constraints

**Version:** 1.0  

---

## 1. Assumptions

| ID | Assumption | Impact if wrong |
|---|---|---|
| A-01 | Kaggle dataset accurately represents Corporación Favorita operations | Findings may not transfer to live business |
| A-02 | Sales values in USD are consistent across the period | Currency/inflation effects not modeled |
| A-03 | `onpromotion` count is known at forecast time for test.csv | If promo plans change last-minute, forecast degrades |
| A-04 | Store open date ≈ first day with sales > 0 | Stores with pre-opening inventory not captured |
| A-05 | National holidays affect all stores equally | Regional/local holidays ignored in v1 |
| A-06 | Oil price is a macro indicator, not a direct store lever | Used for planning assumptions only |
| A-07 | 16-day forecast horizon is sufficient for replenishment planning | Longer horizons need separate model |
| A-08 | LightGBM on tabular features captures cross-series patterns | May miss pure time-series dynamics for new stores |
| A-09 | Training sample (900K rows) is representative of full 2.97M | Full retrain may improve accuracy |
| A-10 | Payday effect is category-specific but measured at basket level in v1 | Aggregate payday uplift (+1.4%) may understate category effects |
| A-11 | Promotion uplift estimates are correlational | Should not be used for ROI budgeting without causal analysis |
| A-12 | No major structural breaks (store closures, format changes) unrecorded in data | Undocumented changes would bias trends |

---

## 2. Constraints

### 2.1 Data constraints

| ID | Constraint | Mitigation |
|---|---|---|
| C-01 | Raw CSVs cannot be committed (Kaggle license + size) | Download instructions in README |
| C-02 | Training data ends 2017-08-15 | Hold-out validation uses last 16 days |
| C-03 | Test labels are private (Kaggle) | External validation via submission only |
| C-04 | transactions missing for ~8.2% of rows | Fill with 0 + flag |
| C-05 | oil.csv has weekday-only entries | Forward/backward fill |
| C-06 | 2017 is partial year in training data | Excluded from YoY KPI comparisons |

### 2.2 Technical constraints

| ID | Constraint | Mitigation |
|---|---|---|
| C-07 | 2-core compute environment for model training | 900K-row sample; document full retrain recommendation |
| C-08 | Batch pipeline only (no streaming) | Acceptable for v1 portfolio project |
| C-09 | Power BI .pbix built locally, not in CI | Guide + data export automated; Streamlit dashboard (`dashboard/app.py`) covers the same KPIs without a manual desktop build step |
| C-10 | Single developer / analyst | Documentation-heavy for handoff |

### 2.3 Business constraints

| ID | Constraint | Mitigation |
|---|---|---|
| C-11 | No access to live ERP/POS systems | Kaggle proxy dataset |
| C-12 | No promotion metadata (discount %, campaign ID) | Use onpromotion count only |
| C-13 | No item/SKU-level data | Category-level analysis only |
| C-14 | Stakeholder interviews simulated | Based on retail best practices + competition brief |

### 2.4 Regulatory / legal constraints

| ID | Constraint | Mitigation |
|---|---|---|
| C-15 | Kaggle competition data redistribution prohibited | Raw data in .gitignore |
| C-16 | No PII in dataset | No additional privacy controls needed |

---

## 3. Dependencies

| Dependency | Type | Status |
|---|---|---|
| Kaggle dataset availability | External | ✅ Available |
| Python 3.10+ | Technical | ✅ |
| LightGBM, pandas, pyarrow | Technical | ✅ requirements.txt |
| Power BI Desktop | Tool | ✅ User-installed |
| GitLab CI runner | Infrastructure | ✅ .gitlab-ci.yml |
| Docker Engine (CI + optional local) | Technical | ✅ Dockerfile, CI `docker-build` stage |
| Streamlit, Plotly | Technical | ✅ requirements.txt |

---

## 4. Related documents

- [01_Project_Charter.md](01_Project_Charter.md)
- [13_Risk_Assessment.md](13_Risk_Assessment.md)
- [11_Business_Rules.md](11_Business_Rules.md)
