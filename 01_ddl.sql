-- ============================================
-- SALES ANALYTICS DATA WAREHOUSE - DDL (v2)
-- Star Schema: 1 Fact Table + 4 Dimension Tables
-- ============================================

-- ---------- DIMENSION: DATE ----------
CREATE TABLE dim_date (
    date_key        INT PRIMARY KEY,          -- format: YYYYMMDD
    full_date        DATE NOT NULL,
    day              INT NOT NULL,
    month            INT NOT NULL,
    month_name       VARCHAR(20) NOT NULL,
    quarter          INT NOT NULL,
    year             INT NOT NULL,
    day_of_week      VARCHAR(15) NOT NULL,
    is_weekend       BOOLEAN NOT NULL
);

-- ---------- DIMENSION: PRODUCT ----------
CREATE TABLE dim_product (
    product_key      SERIAL PRIMARY KEY,
    product_id       VARCHAR(30) NOT NULL,     -- natural key from source system
    product_name     VARCHAR(200) NOT NULL,
    category         VARCHAR(100),
    sub_category     VARCHAR(100)
);

-- ---------- DIMENSION: REGION (replaces dim_store) ----------
CREATE TABLE dim_region (
    region_key       SERIAL PRIMARY KEY,
    region_name      VARCHAR(100) NOT NULL,    -- e.g. East, West, Central, South
    country          VARCHAR(100)
);

-- ---------- DIMENSION: CUSTOMER (SCD Type 2 ready) ----------
CREATE TABLE dim_customer (
    customer_key     SERIAL PRIMARY KEY,       -- surrogate key
    customer_id      VARCHAR(20) NOT NULL,     -- natural/business key
    customer_name    VARCHAR(150) NOT NULL,
    segment          VARCHAR(50),
    city             VARCHAR(100),
    state            VARCHAR(100),
    start_date       DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date         DATE NOT NULL DEFAULT '9999-12-31',
    is_current       BOOLEAN NOT NULL DEFAULT TRUE
);

-- ---------- FACT: SALES ----------
CREATE TABLE fact_sales (
    sale_key         SERIAL PRIMARY KEY,
    sale_id          VARCHAR(30) NOT NULL,     -- original Order ID
    date_key         INT NOT NULL REFERENCES dim_date(date_key),
    product_key      INT NOT NULL REFERENCES dim_product(product_key),
    customer_key     INT NOT NULL REFERENCES dim_customer(customer_key),
    region_key       INT NOT NULL REFERENCES dim_region(region_key),
    quantity         INT NOT NULL,
    discount         NUMERIC(5,2) DEFAULT 0,
    total_amount     NUMERIC(12,2) NOT NULL,
    profit           NUMERIC(12,2)
);

-- ---------- INDEXES for query performance ----------
CREATE INDEX idx_fact_sales_date ON fact_sales(date_key);
CREATE INDEX idx_fact_sales_product ON fact_sales(product_key);
CREATE INDEX idx_fact_sales_customer ON fact_sales(customer_key);
CREATE INDEX idx_fact_sales_region ON fact_sales(region_key);
CREATE INDEX idx_customer_natural_key ON dim_customer(customer_id, is_current);
