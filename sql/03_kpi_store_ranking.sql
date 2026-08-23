-- Store ranking by total sales (phase3 equivalent)

SELECT
    store_nbr,
    city,
    state,
    store_type,
    SUM(sales) AS total_sales,
    AVG(sales) AS avg_daily_sales_per_row,
    RANK() OVER (ORDER BY SUM(sales) DESC) AS sales_rank
FROM cleaned_train
GROUP BY store_nbr, city, state, store_type
ORDER BY total_sales DESC;
