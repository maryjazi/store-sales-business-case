# 04 — Interview Notes

**Version:** 1.0  
**Method:** Structured stakeholder interviews (simulated for portfolio project; aligned with Kaggle competition context and retail best practices)

---

## Interview 1 — Retail Operations Director

**Date:** Week 1, Day 1  
**Duration:** 60 min  
**Attendees:** Operations Director, Data Analyst  

### Key questions & responses

**Q: What is the biggest planning challenge today?**  
> "We plan store staffing and inventory using last week's averages. Weekends and holidays catch us off guard — we either overstaff or run out of stock on high-demand categories."

**Q: What decisions would better forecasts enable?**  
> "Replenishment orders 1–2 weeks ahead, especially for Grocery, Beverages, and Produce — they are most of our revenue. If we could predict demand by store and category daily, supply chain could cut waste."

**Q: How do you measure store performance today?**  
> "Total sales ranking by store. But I know some stores opened recently and look bad on raw totals. We need a fair comparison."

**Q: What external factors matter?**  
> "National holidays definitely. Oil price — Ecuador's economy moves with oil, so when oil drops, consumer spending feels it. Not sure how much at store level."

### Requirements extracted
- Daily demand forecast, store × category, 16-day horizon minimum
- Calendar-aware planning (weekends, holidays)
- Store ranking adjusted for store age
- Executive KPI dashboard

---

## Interview 2 — Merchandising Manager

**Date:** Week 1, Day 2  
**Duration:** 45 min  

### Key questions & responses

**Q: Which categories matter most?**  
> "Grocery I, Beverages, Produce — if we lose a day of stock there, it hurts. School supplies spike only during promo season."

**Q: How do you evaluate promotions?**  
> "We look at sales during promo weeks vs non-promo. But I'm not sure we're controlling for category mix — some categories barely sell without promos."

**Q: What KPIs do you track?**  
> "Category share of total sales, promo uptake (`onpromotion` count), and which families grow YoY."

### Requirements extracted
- Category revenue share and ranking
- Promotion correlation analysis (with caveat: not causal)
- Category-group drill-down in dashboard

---

## Interview 3 — Supply Chain Lead

**Date:** Week 1, Day 3  
**Duration:** 45 min  

### Key questions & responses

**Q: What forecast granularity do you need?**  
> "Store number, product family, date — same grain as our sales history. One number per day per SKU group."

**Q: What accuracy is acceptable?**  
> "Better than our 28-day moving average. If ML can beat that by 10%, we'd pilot it on top 3 categories first."

**Q: What data can't you use at forecast time?**  
> "Same-day transaction counts — we don't know those until the day happens. Don't put them in the model."

### Requirements extracted
- Forecast at id grain (store × family × date)
- Baseline comparison: moving average, same-weekday average
- Exclude same-day transaction count from features (leakage)

---

## Interview 4 — Regional Store Manager (Quito)

**Date:** Week 2, Day 1  
**Duration:** 30 min  

### Key questions & responses

**Q: What patterns do you see locally?**  
> "Quito stores are our highest volume. Type A stores outperform Type C in smaller cities — but city matters more than type alone."

**Q: Anything surprising in the data?**  
> "Payday — we expected a bigger bump on the 15th and month-end. Maybe it's category-specific."

### Requirements extracted
- City and store-type breakdowns in dashboard
- Category-level payday analysis flagged as future work

---

## Consolidated themes

| Theme | Mentioned by | Priority |
|---|---|---|
| Better demand forecasting | Ops, Supply Chain | P0 |
| Calendar effects (weekend/holiday) | Ops, Merchandising | P0 |
| Fair store comparison (lifecycle) | Ops, Regional Manager | P1 |
| Category concentration risk | Merchandising, Ops | P1 |
| Promotion ROI (causal) | Merchandising | P2 (next phase) |
| Oil price macro signal | Ops | P2 |

---

## Related documents

- [02_Business_Requirements.md](02_Business_Requirements.md)
- [03_Stakeholders.md](03_Stakeholders.md)
- [06_KPI_Definition.md](06_KPI_Definition.md)
