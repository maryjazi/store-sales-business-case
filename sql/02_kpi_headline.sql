-- Headline KPIs (phase3 equivalent) on merged/cleaned sales table.
-- Replace `cleaned_train` with your merged view or materialized table.

SELECT
    SUM(sales) AS total_sales,
    COUNT(DISTINCT date) AS trading_days,
    AVG(daily_total) AS avg_daily_sales,
    100.0 * AVG(CASE WHEN sales = 0 THEN 1.0 ELSE 0.0 END) AS pct_zero_sales_days
FROM cleaned_train
CROSS JOIN LATERAL (
    SELECT SUM(sales) AS daily_total
    FROM cleaned_train c2
    WHERE c2.date = cleaned_train.date
    GROUP BY c2.date
) d;

-- YoY growth (exclude partial 2017)
SELECT
    year,
    SUM(sales) AS yearly_sales,
    ROUND(
        100.0 * (SUM(sales) / LAG(SUM(sales)) OVER (ORDER BY year) - 1),
        1
    ) AS yoy_pct
FROM cleaned_train
WHERE year BETWEEN 2013 AND 2016
GROUP BY year
ORDER BY year;
