# Pricing & Profitability — simulated commercial scenario

All monetary figures on this page are **simulated** (see `docs/19_Simulation_Design.md`).
Quantities are the real observed units; what they were worth is modelled.

## 1. Which quantity carries the revenue

| View | Units | Revenue (simulated) |
|---|---|---|
| Demand-side (observed units, phase 6) | 1073644952 | 2297126088 USD |
| **Fulfilled (canonical from B2 onward)** | 1057851662 | **2263204070 USD** |
| Shortfall — could not be served in this scenario | 15793291 | 33922019 USD (1.48%) |

Revenue is booked on **fulfilled** quantity. Booking it on observed units would credit
the scenario with goods that, inside the same scenario, were not on the shelf. The
shortfall is a limitation of this simulated supply chain, not Favorita's lost sales.

## 2. Headline profitability (simulated)

| KPI | Value |
|---|---|
| Revenue at list price | 2457404305 USD |
| Markdown given away | 194200235 USD (7.9% of list) |
| Net revenue | 2263204070 USD |
| COGS | 1752116518 USD |
| Gross margin | 511087552 USD (22.6%) |

## 3. Margin extremes by family (simulated)

| family      |   gross_margin_pct_sim |   markdown_pct_sim |     revenue_sim |
|:------------|-----------------------:|-------------------:|----------------:|
| LINGERIE    |                 54.347 |              0.694 |     6.43942e+06 |
| LADIESWEAR  |                 51.788 |              0.208 |     9.78281e+06 |
| BEAUTY      |                 41.888 |              5.546 |     2.11581e+06 |
| CELEBRATION |                 39.275 |              1.028 |     3.69715e+06 |
| BOOKS       |                 35.176 |              0     | 59079.3         |

| family    |   gross_margin_pct_sim |   markdown_pct_sim |   revenue_sim |
|:----------|-----------------------:|-------------------:|--------------:|
| GROCERY I |                 18.047 |             10.896 |   5.06331e+08 |
| POULTRY   |                 19.66  |              4.454 |   1.33136e+08 |
| PRODUCE   |                 20.027 |              7.474 |   1.6652e+08  |
| MEATS     |                 20.289 |              4.914 |   1.71756e+08 |
| HOME CARE |                 21.225 |              9.833 |   5.13221e+07 |

## 4. Margin bridge

The year-on-year change in gross margin, split into volume, price and cost effects.
The decomposition is computed per family and summed, so it closes exactly and needs no
residual mix term. Full table: `data/processed/kpi_margin_bridge_sim.csv`.

|   year |   margin_change_sim |   volume_effect_sim |   price_effect_sim |   cost_effect_sim |
|-------:|--------------------:|--------------------:|-------------------:|------------------:|
|   2014 |         2.58431e+07 |         3.74541e+07 |       -5.3096e+06  |      -6.30138e+06 |
|   2015 |         6.62164e+06 |         2.02373e+07 |       -5.72261e+06 |      -7.89308e+06 |
|   2016 |        -2.19475e+07 |         1.8655e+07  |       -3.18883e+07 |      -8.71415e+06 |
|   2017 |        -4.40342e+07 |        -3.52353e+07 |       -3.82536e+06 |      -4.97351e+06 |
