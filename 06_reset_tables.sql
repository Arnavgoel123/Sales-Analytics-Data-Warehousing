-- Run this to reset everything before re-running the ETL
TRUNCATE TABLE fact_sales, dim_product, dim_customer, dim_region, dim_date
RESTART IDENTITY CASCADE;
