# 26 — Commercial Cockpit Design (B8)

**Version:** 1.0  
**Last updated:** September 2026  
**Implemented by:** `etl/phase13_commercial_export.py`, `dashboard/cockpit_data.py`, `dashboard/commercial_app.py`  
**Outputs:** `dashboard/commercial/` (5 tables) + `dashboard/commercial/POWERBI_COMMERCIAL_GUIDE.md`

---

## 1. What B8 is

The last step of Track 2: one model behind one cockpit, in four views — **Executive,
Pricing, Procurement, Retail** — reading the same monthly star schema from both Power BI and
Streamlit. It adds no analysis. Everything on it was computed in phases 8–12; this phase
aggregates to month grain, declares provenance, and draws.

| Table | Grain |
|---|---|
| `fact_commercial_monthly` | month × store × family (99,792 rows) |
| `fact_procurement_monthly` | month × store × family × supplier (127,411 rows) |
| `dim_family_commercial`, `dim_supplier_commercial` | dimensions |
| `dim_measure_provenance` | one row per measure — see §2 |

The cockpit totals are asserted against the committed phase-9 KPIs: 2,263,204,070 USD
simulated revenue, 22.6% gross margin, 1,770,274,645 USD procurement spend. An aggregation
that does not land on the numbers the pipeline already committed is a recalculation, and the
test suite fails it.

---

## 2. Provenance becomes data

Rule P-06 (docs/19 §2) says every monetary figure is labelled as simulated wherever it
appears. Until this phase that rule lived in documentation and in review discipline — which
is exactly the kind of rule that survives until the day someone is in a hurry.

So it became a table. `dim_measure_provenance.csv` maps every measure in the model to a tier:

| Tier | Meaning | Label suffix |
|---|---|---|
| `REAL` | observed in the dataset | *(none)* |
| `SIMULATED` | produced by the phase-6/7 rules | `(simulated)` |
| `DERIVED` | arithmetic on the above; inherits the weakest tier | `(simulated)` |
| `OBSERVATIONAL_ESTIMATE` | estimated from real inputs against a matched baseline (B5) | `(observational estimate)` |

`cockpit_data.label_for()` builds every title from that table and **raises on a measure with
no entry**. The export refuses to write a model containing an undeclared measure. A test
checks both. The dashboard cannot show a number without saying what it rests on — not because
someone remembered, but because the alternative does not run.

The Power BI guide carries the same rule into DAX: measure names are
`Revenue (simulated)`, not `Revenue`.

---

## 3. Chart rules

The cockpit follows three rules worth stating, because each prevents a specific
misreading:

- **One axis per chart.** Revenue and margin % belong on the Executive page together, but as
  two charts. A dual-axis chart lets the reader infer a relationship from where two lines
  happen to cross, which is a function of the axis scaling, not the data.
- **Ratios of sums, never means of ratios**, everywhere — the same rule the promotion phase
  had to learn (docs/24 §2).
- **Colour carries identity, never rank**, with at most three categorical series on one chart
  and a diverging pair (blue/red around a neutral) reserved for signed gaps such as the
  uplift-versus-break-even bar.

---

## 4. Why both Power BI and Streamlit

The Power BI report is what a stakeholder expects; the Streamlit cockpit is what can be
demonstrated in a browser with `streamlit run` and no desktop licence, and what can be tested
in CI. They read **the same five files**, so they cannot disagree about a number.

The `.pbix` itself is built in Power BI Desktop from
`dashboard/commercial/POWERBI_COMMERCIAL_GUIDE.md` and is not committed (see `.gitignore`).
The repo is honest about that: what exists here is the model, the guide and the working
Streamlit cockpit — not a screenshot of a file nobody can open.

---

## 5. Related documents

- [19_Simulation_Design.md](19_Simulation_Design.md) §2 — the provenance rules this phase turns into data
- [22_Pricing_Profitability.md](22_Pricing_Profitability.md) · [24_Promotion_Effectiveness_Design.md](24_Promotion_Effectiveness_Design.md) · [25_Scenario_Design.md](25_Scenario_Design.md)
- [17_Dashboard_Design.md](17_Dashboard_Design.md) — the original sales dashboard design
