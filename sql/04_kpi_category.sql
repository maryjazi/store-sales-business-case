-- Category (product family) performance

SELECT
    family,
    SUM(sales) AS total_sales,
    ROUND(100.0 * SUM(sales) / SUM(SUM(sales)) OVER (), 2) AS pct_of_total,
    AVG(sales) AS avg_sales,
    RANK() OVER (ORDER BY SUM(sales) DESC) AS category_rank
FROM cleaned_train
GROUP BY family
ORDER BY total_sales DESC;
