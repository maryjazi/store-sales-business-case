-- Phase 0 equivalent: merge train with dimension and external-factor tables.
-- Assumes tables: train, stores, oil, holidays_events, transactions

WITH oil_daily AS (
    SELECT
        d::date AS date,
        LAST_VALUE(dcoilwtico IGNORE NULLS) OVER (
            ORDER BY d ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS dcoilwtico
    FROM (
        SELECT generate_series(
            (SELECT MIN(date) FROM oil),
            (SELECT MAX(date) FROM oil),
            '1 day'::interval
        )::date AS d
    ) cal
    LEFT JOIN oil o ON o.date = cal.d
),
national_holidays AS (
    SELECT DISTINCT ON (date)
        date,
        type AS holiday_type,
        description AS holiday_description
    FROM holidays_events
    WHERE locale = 'National'
      AND transferred = FALSE
    ORDER BY date, description
)
SELECT
    t.id,
    t.date,
    t.store_nbr,
    t.family,
    t.sales,
    t.onpromotion,
    s.city,
    s.state,
    s.type AS store_type,
    s.cluster,
    od.dcoilwtico,
    tx.transactions,
    nh.holiday_type,
    nh.holiday_description,
    (nh.date IS NOT NULL) AS is_holiday
FROM train t
LEFT JOIN stores s ON s.store_nbr = t.store_nbr
LEFT JOIN oil_daily od ON od.date = t.date
LEFT JOIN transactions tx ON tx.date = t.date AND tx.store_nbr = t.store_nbr
LEFT JOIN national_holidays nh ON nh.date = t.date;
