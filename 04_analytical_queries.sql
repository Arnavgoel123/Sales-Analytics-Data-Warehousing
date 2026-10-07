-- ============================================
-- ANALYTICAL QUERIES ON THE SALES WAREHOUSE
-- ============================================

-- 1. Total revenue and profit by region
SELECT
    r.region_name,
    SUM(f.total_amount) AS total_revenue,
    SUM(f.profit)        AS total_profit
FROM fact_sales f
JOIN dim_region r ON f.region_key = r.region_key
GROUP BY r.region_name
ORDER BY total_revenue DESC;


-- 2. Monthly sales trend for a given year
SELECT
    d.year,
    d.month,
    d.month_name,
    SUM(f.total_amount) AS monthly_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.year = 2023
GROUP BY d.year, d.month, d.month_name
ORDER BY d.month;


-- 3. Top 10 products by revenue
SELECT
    p.product_name,
    p.category,
    SUM(f.total_amount) AS revenue,
    SUM(f.quantity)     AS units_sold
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.product_name, p.category
ORDER BY revenue DESC
LIMIT 10;


-- 4. Revenue by category and quarter (ROLLUP for subtotals + grand total)
SELECT
    p.category,
    d.quarter,
    SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY ROLLUP (p.category, d.quarter)
ORDER BY p.category, d.quarter;


-- 5. Running total of revenue by month (window function)
SELECT
    d.year,
    d.month,
    SUM(f.total_amount) AS monthly_revenue,
    SUM(SUM(f.total_amount)) OVER (
        PARTITION BY d.year ORDER BY d.month
    ) AS running_total
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month
ORDER BY d.year, d.month;


-- 6. Rank products within each category by revenue (window function)
SELECT
    category,
    product_name,
    revenue,
    RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS rank_in_category
FROM (
    SELECT
        p.category,
        p.product_name,
        SUM(f.total_amount) AS revenue
    FROM fact_sales f
    JOIN dim_product p ON f.product_key = p.product_key
    GROUP BY p.category, p.product_name
) sub
ORDER BY category, rank_in_category;


-- 7. Customer segment performance
SELECT
    c.segment,
    COUNT(DISTINCT c.customer_id) AS num_customers,
    SUM(f.total_amount)           AS total_revenue,
    AVG(f.total_amount)           AS avg_order_value
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY c.segment
ORDER BY total_revenue DESC;


-- 8. Weekend vs weekday sales comparison
SELECT
    d.is_weekend,
    COUNT(*)              AS num_orders,
    SUM(f.total_amount)   AS total_revenue,
    AVG(f.total_amount)   AS avg_order_value
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.is_weekend;


-- 9. SCD-aware query: sales attributed to customer's city AT TIME OF SALE
-- (works correctly even if a customer has moved since, because fact_sales
--  stores the customer_key of the SPECIFIC dim_customer row active then)
SELECT
    c.city,
    c.state,
    SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY c.city, c.state
ORDER BY revenue DESC
LIMIT 10;


-- 10. Year-over-year growth by category
WITH yearly AS (
    SELECT
        p.category,
        d.year,
        SUM(f.total_amount) AS revenue
    FROM fact_sales f
    JOIN dim_product p ON f.product_key = p.product_key
    JOIN dim_date d ON f.date_key = d.date_key
    GROUP BY p.category, d.year
)
SELECT
    category,
    year,
    revenue,
    LAG(revenue) OVER (PARTITION BY category ORDER BY year) AS prev_year_revenue,
    ROUND(
        100.0 * (revenue - LAG(revenue) OVER (PARTITION BY category ORDER BY year))
        / NULLIF(LAG(revenue) OVER (PARTITION BY category ORDER BY year), 0), 2
    ) AS yoy_growth_pct
FROM yearly
ORDER BY category, year;
