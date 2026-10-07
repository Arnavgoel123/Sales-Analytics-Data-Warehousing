# Sales Analytics Data Warehouse

A star-schema sales analytics data warehouse built on PostgreSQL, with an ETL
pipeline, SCD Type 2 historical tracking, analytical SQL queries, and an ML
layer (demand forecasting, customer segmentation, market basket analysis),
visualized through an interactive Streamlit dashboard.

## Architecture

- **Database**: PostgreSQL — star schema (1 fact table + 4 dimension tables)
- **ETL**: Python (pandas, psycopg2) loading the Superstore dataset
- **SCD Type 2**: implemented both in Python and as a PL/pgSQL stored procedure
- **ML**: Prophet (forecasting), scikit-learn (K-Means segmentation), mlxtend (market basket analysis)
- **Dashboard**: Streamlit + Plotly

## Schema

```
dim_date ---\
dim_product --\
                >---  fact_sales
dim_region ---/
dim_customer -/
```

See `er_diagram.png` for the full entity-relationship diagram.

## Setup

1. Install PostgreSQL and create a database:
   ```sql
   CREATE DATABASE sales_dw;
   ```

2. Install Python dependencies:
   ```bash
   pip install pandas psycopg2-binary prophet matplotlib scikit-learn mlxtend streamlit plotly python-dotenv
   ```

3. Download the [Sample Superstore dataset](https://www.kaggle.com/datasets/vivek468/superstore-dataset-final) and place the CSV in this folder.

4. Copy `.env.example` to `.env` and fill in your real database credentials. `.env` is git-ignored and never committed.

## Run order

| Step | File | How |
|---|---|---|
| 1 | `01_ddl.sql` | Run in pgAdmin / psql |
| 2 | `00_populate_dim_date.sql` | Run in pgAdmin / psql |
| 3 | `02_etl.py` | `python 02_etl.py` |
| 4 | `04_analytical_queries.sql` | Run in pgAdmin / psql |
| 5 | `08_view_and_procedure.sql` | Run in pgAdmin / psql |
| 6 | `05_forecast.py` | `python 05_forecast.py` |
| 7 | `07_customer_segmentation.py` | `python 07_customer_segmentation.py` |
| 8 | `09_market_basket.py` | `python 09_market_basket.py` |
| 9 | `10_dashboard.py` | `streamlit run 10_dashboard.py` |

Optional: `03_scd_update.py` — demonstrates SCD Type 2 with a sample customer-change CSV.

## Features

- Star schema with surrogate keys and foreign-key-enforced referential integrity
- SCD Type 2 customer dimension (full change history preserved)
- Indexed fact table for query performance
- Reusable SQL view (`monthly_sales_summary`) and stored procedure (`apply_customer_scd`)
- Analytical queries: joins, `ROLLUP`, window functions (`RANK`, `LAG`, running totals)
- Prophet-based revenue forecasting with confidence intervals
- RFM + K-Means customer segmentation
- Apriori-based market basket analysis
- Interactive dashboard across 4 views: revenue, products, segments, forecast

## Author

Arnav Goel — DBMS Lab Project
