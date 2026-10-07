-- ============================================
-- POPULATE dim_date
-- Generates one row per day for a given range
-- Run this once, right after 01_ddl.sql
-- ============================================

INSERT INTO dim_date (
    date_key,
    full_date,
    day,
    month,
    month_name,
    quarter,
    year,
    day_of_week,
    is_weekend
)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INT               AS date_key,
    d                                          AS full_date,
    EXTRACT(DAY FROM d)::INT                   AS day,
    EXTRACT(MONTH FROM d)::INT                 AS month,
    TO_CHAR(d, 'Month')                        AS month_name,
    EXTRACT(QUARTER FROM d)::INT               AS quarter,
    EXTRACT(YEAR FROM d)::INT                  AS year,
    TO_CHAR(d, 'Day')                          AS day_of_week,
    CASE WHEN EXTRACT(ISODOW FROM d) IN (6,7) THEN TRUE ELSE FALSE END AS is_weekend
FROM GENERATE_SERIES(
    '2010-01-01'::DATE,
    '2026-12-31'::DATE,
    '1 day'::INTERVAL
) AS d;
