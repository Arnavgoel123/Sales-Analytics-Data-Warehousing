-- ============================================
-- ADDITIONAL DBMS FEATURES: VIEW + STORED PROCEDURE
-- ============================================

-- ---------- VIEW: monthly sales summary ----------
-- Wraps a common analytical query so it can be queried like a table,
-- without repeating the JOIN/GROUP BY logic every time.
CREATE OR REPLACE VIEW monthly_sales_summary AS
SELECT
    d.year,
    d.month,
    d.month_name,
    r.region_name,
    p.category,
    SUM(f.total_amount) AS total_revenue,
    SUM(f.profit)        AS total_profit,
    COUNT(DISTINCT f.sale_id) AS num_orders
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
JOIN dim_region r ON f.region_key = r.region_key
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY d.year, d.month, d.month_name, r.region_name, p.category;

-- Usage example (no JOINs needed anymore, just query the view):
-- SELECT * FROM monthly_sales_summary WHERE year = 2017 ORDER BY month;


-- ---------- STORED PROCEDURE: apply a customer update (SCD Type 2) ----------
-- Pushes the SCD Type 2 logic into the database itself, callable from
-- SQL directly instead of only from the Python script.
CREATE OR REPLACE PROCEDURE apply_customer_scd(
    p_customer_id   VARCHAR,
    p_customer_name VARCHAR,
    p_segment       VARCHAR,
    p_city          VARCHAR,
    p_state         VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_existing RECORD;
BEGIN
    -- look up the current active row for this customer
    SELECT customer_name, segment, city, state
    INTO v_existing
    FROM dim_customer
    WHERE customer_id = p_customer_id AND is_current = TRUE;

    IF NOT FOUND THEN
        -- brand new customer
        INSERT INTO dim_customer
            (customer_id, customer_name, segment, city, state,
             start_date, end_date, is_current)
        VALUES
            (p_customer_id, p_customer_name, p_segment, p_city, p_state,
             CURRENT_DATE, '9999-12-31', TRUE);

    ELSIF v_existing.customer_name IS DISTINCT FROM p_customer_name
       OR v_existing.segment       IS DISTINCT FROM p_segment
       OR v_existing.city          IS DISTINCT FROM p_city
       OR v_existing.state         IS DISTINCT FROM p_state THEN

        -- something changed: close old row, insert new version
        UPDATE dim_customer
        SET end_date = CURRENT_DATE, is_current = FALSE
        WHERE customer_id = p_customer_id AND is_current = TRUE;

        INSERT INTO dim_customer
            (customer_id, customer_name, segment, city, state,
             start_date, end_date, is_current)
        VALUES
            (p_customer_id, p_customer_name, p_segment, p_city, p_state,
             CURRENT_DATE, '9999-12-31', TRUE);
    END IF;
    -- else: no change, do nothing
END;
$$;

-- Usage example:
-- CALL apply_customer_scd('AB-10015', 'Aaron Bergman', 'Consumer', 'Pune', 'Maharashtra');
