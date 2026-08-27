-- Monthly sales trend with optional oil price join

SELECT
    DATE_TRUNC('month', date)::date AS month,
    SUM(sales) AS monthly_sales,
    AVG(dcoilwtico) AS avg_oil_price
FROM cleaned_train
GROUP BY 1
ORDER BY 1;
