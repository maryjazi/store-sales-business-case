# 03 — Stakeholders

**Version:** 1.0  

---

## 1. Stakeholder register

| ID | Name / Role | Organization | Interest | Influence | Engagement |
|---|---|---|---|---|---|
| STK-01 | Retail Operations Director | Corporación Favorita | Overall sales performance, staffing | High | Sponsor |
| STK-02 | Merchandising Manager | Product categories | Category mix, promotions, stock levels | High | Key user |
| STK-03 | Regional Store Managers (5 regions) | Store operations | Store rankings, local demand patterns | Medium | Key user |
| STK-04 | Inventory / Supply Chain Lead | Logistics | Demand forecasts for replenishment | High | Key user |
| STK-05 | Finance / FP&A Analyst | Finance | Revenue growth, YoY targets | Medium | Informed |
| STK-06 | BI / IT Team | Technology | Dashboard hosting, data pipeline | Medium | Support |
| STK-07 | Data Analyst (Project Lead) | Analytics | End-to-end delivery | High | Responsible |
| STK-08 | Store Staff (54 locations) | Operations | Indirect — affected by staffing/inventory decisions | Low | Informed |

> **Note:** This project uses the public Kaggle dataset as a proxy for Corporación Favorita. Stakeholder roles are modeled on a typical multi-store grocery retailer.

---

## 2. RACI matrix

| Activity | Operations Director | Merchandising | Regional Managers | Supply Chain | Data Analyst |
|---|---|---|---|---|---|
| Define business questions | A | C | C | C | R |
| Approve KPI framework | A | C | I | I | R |
| Data cleaning rules | I | C | I | I | R/A |
| EDA & findings review | I | C | C | I | R |
| Forecast model selection | C | I | I | A | R |
| Dashboard design | C | C | C | I | R |
| Business recommendations | A | C | C | C | R |

**Legend:** R = Responsible, A = Accountable, C = Consulted, I = Informed

---

## 3. Stakeholder needs summary

### STK-01 — Retail Operations Director
- **Needs:** Headline revenue KPIs, growth trend, forecast accuracy for planning
- **Pain points:** Manual Excel reports; no unified view across 54 stores
- **Success metric:** Can answer "Are we on track?" in one dashboard view

### STK-02 — Merchandising Manager
- **Needs:** Category concentration, promotion impact, holiday calendar planning
- **Pain points:** Promotion ROI unclear; category mix shifts not visible
- **Success metric:** Category-level KPIs drive promo calendar decisions

### STK-03 — Regional Store Managers
- **Needs:** Store ranking adjusted for tenure; city/type comparisons
- **Pain points:** Raw total sales unfairly penalize new stores (e.g. store 52)
- **Success metric:** Fair performance comparisons using lifecycle-adjusted metrics

### STK-04 — Supply Chain / Inventory Lead
- **Needs:** 16-day forward demand forecast at store × category level
- **Pain points:** Moving-average planning misses seasonality and store effects
- **Success metric:** Forecast RMSLE < 0.50, beat moving average by ≥ 10%

---

## 4. Communication plan

| Audience | Channel | Frequency | Content |
|---|---|---|---|
| Sponsor | Executive summary / business case | Project completion | Findings + recommendations |
| Merchandising & Ops | KPI report + dashboard demo | Monthly (post go-live) | KPI tables, trend charts |
| Supply Chain | Forecast CSV export | Daily refresh (future state) | `forecast_detail.parquet` |
| Project team | GitLab / documentation | Continuous | ETL logs, test results |

---

## 5. Related documents

- [04_Interview_Notes.md](04_Interview_Notes.md)
- [01_Project_Charter.md](01_Project_Charter.md)
- [14_Use_Cases.md](14_Use_Cases.md)
